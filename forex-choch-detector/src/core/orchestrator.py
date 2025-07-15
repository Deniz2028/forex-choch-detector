python"""
Ana orkestratör - tüm servisleri koordine eden merkezi sınıf
"""
import asyncio
import signal
import logging
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager
import structlog

# Relative import'ları absolute yap
from data_feed.base import DataFeedBase
from data_feed.oanda import OandaFeed
from data_feed.mt5 import MT5Feed
from data_feed.websocket import WebSocketFeed
from pattern.choch_detector import CHoCHDetector
from region.box_region import BoxRegionManager
from notifier.telegram import TelegramNotifier
from notifier.desktop import DesktopNotifier
from notifier.email import EmailNotifier
from core.config import Config

logger = structlog.get_logger(__name__)

class TradingOrchestrator:
    """Ana orkestratör sınıfı - tüm bileşenleri yönetir"""
    
    def __init__(self, config: Config):
        self.config = config
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Bileşenler
        self.data_feed: Optional[DataFeedBase] = None
        self.pattern_detector = CHoCHDetector(config.pattern)
        self.region_manager = BoxRegionManager()
        self.notifiers: List = []
        
        # Aktif semboller
        self.active_symbols: Set[str] = set()
        
        # Sinyal handlers
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self) -> None:
        """Sistem sinyallerini yakala"""
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Sinyal handler - graceful shutdown"""
        logger.info("Shutdown sinyali alındı", signal=signum)
        asyncio.create_task(self.shutdown())
    
    async def initialize(self) -> None:
        """Tüm bileşenleri başlat"""
        logger.info("Sistem başlatılıyor...")
        
        # Data feed oluştur
        self.data_feed = self._create_data_feed()
        
        # Notifier'ları başlat
        await self._setup_notifiers()
        
        # Pattern detector event handler'larını bağla
        self.pattern_detector.on_choch = self._on_choch_detected
        self.pattern_detector.on_bos = self._on_bos_detected
        
        # Data feed event handler'larını bağla
        self.data_feed.on_tick = self._on_tick_received
        self.data_feed.on_error = self._on_feed_error
        
        logger.info("Sistem başarıyla başlatıldı")
    
    def _create_data_feed(self) -> DataFeedBase:
        """Broker tipine göre data feed oluştur"""
        broker_type = self.config.broker.type.lower()
        
        if broker_type == "oanda":
            return OandaFeed(
                api_key=self.config.broker.api_key,
                account_id=self.config.broker.account_id,
                environment=self.config.broker.environment
            )
        elif broker_type == "mt5":
            return MT5Feed()
        elif broker_type == "websocket":
            return WebSocketFeed()
        else:
            raise ValueError(f"Desteklenmeyen broker türü: {broker_type}")
    
    async def _setup_notifiers(self) -> None:
        """Bildirim servislerini başlat"""
        if self.config.notifications.telegram and self.config.notifications.telegram.enabled:
            telegram_notifier = TelegramNotifier(
                bot_token=self.config.notifications.telegram.bot_token,
                chat_id=self.config.notifications.telegram.chat_id
            )
            await telegram_notifier.initialize()
            self.notifiers.append(telegram_notifier)
        
        if self.config.notifications.desktop_enabled:
            desktop_notifier = DesktopNotifier()
            await desktop_notifier.initialize()
            self.notifiers.append(desktop_notifier)
        
        if self.config.notifications.email_enabled:
            email_notifier = EmailNotifier(
                smtp_host=self.config.notifications.smtp_host,
                smtp_port=self.config.notifications.smtp_port,
                smtp_user=self.config.notifications.smtp_user,
                smtp_password=self.config.notifications.smtp_password
            )
            await email_notifier.initialize()
            self.notifiers.append(email_notifier)
    
    async def run(self) -> None:
        """Ana çalışma döngüsü"""
        if not self.data_feed:
            await self.initialize()
        
        self.running = True
        logger.info("Trading sistemi çalışmaya başladı")
        
        try:
            # Sembolleri subscribe et
            for symbol in self.config.broker.symbols:
                await self.data_feed.subscribe(symbol)
                self.active_symbols.add(symbol)
            
            # Ana döngü
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error("Ana döngüde hata", error=str(e))
            raise
        finally:
            await self.cleanup()
    
    async def _on_tick_received(self, symbol: str, tick_data: Dict) -> None:
        """Yeni tick verisi geldiğinde çağrılır"""
        try:
            # Pattern detection
            await self.pattern_detector.process_tick(symbol, tick_data)
            
            # Region kontrolü
            await self.region_manager.check_regions(symbol, tick_data)
            
        except Exception as e:
            logger.error("Tick işleme hatası", symbol=symbol, error=str(e))
    
    async def _on_choch_detected(self, symbol: str, choch_data: Dict) -> None:
        """CHoCH tespit edildiğinde çağrılır"""
        message = f"🔄 CHoCH Detected: {symbol}\n"
        message += f"Direction: {choch_data['direction']}\n"
        message += f"Price: {choch_data['price']}\n"
        message += f"Time: {choch_data['timestamp']}"
        
        await self._send_notification(message, alert_type="choch")
        
        logger.info("CHoCH tespit edildi", symbol=symbol, data=choch_data)
    
    async def _on_bos_detected(self, symbol: str, bos_data: Dict) -> None:
        """BOS tespit edildiğinde çağrılır"""
        message = f"💥 BOS Detected: {symbol}\n"
        message += f"Direction: {bos_data['direction']}\n"
        message += f"Price: {bos_data['price']}\n"
        message += f"Time: {bos_data['timestamp']}"
        
        await self._send_notification(message, alert_type="bos")
        
        logger.info("BOS tespit edildi", symbol=symbol, data=bos_data)
    
    async def _on_feed_error(self, error: Exception) -> None:
        """Data feed hatası durumunda çağrılır"""
        logger.error("Data feed hatası", error=str(error))
        await self._reconnect_feed()
    
    async def _reconnect_feed(self) -> None:
        """Data feed yeniden bağlantı"""
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(base_delay * (2 ** attempt))
                
                await self.data_feed.disconnect()
                await self.data_feed.connect()
                
                # Sembolleri yeniden subscribe et
                for symbol in self.active_symbols:
                    await self.data_feed.subscribe(symbol)
                
                logger.info("Data feed yeniden bağlandı")
                return
                
            except Exception as e:
                logger.warning(f"Yeniden bağlanma denemesi {attempt + 1} başarısız", error=str(e))
        
        logger.error("Yeniden bağlanma başarısız - sistem durduruluyor")
        await self.shutdown()
    
    async def _send_notification(self, message: str, alert_type: str = "info") -> None:
        """Tüm notifier'lara bildirim gönder"""
        tasks = []
        for notifier in self.notifiers:
            tasks.append(notifier.send_notification(message, alert_type))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def shutdown(self) -> None:
        """Sistemi kapat"""
        logger.info("Sistem kapatılıyor...")
        self.running = False
        self.shutdown_event.set()
    
    async def cleanup(self) -> None:
        """Temizlik işlemleri"""
        if self.data_feed:
            await self.data_feed.disconnect()
        
        for notifier in self.notifiers:
            if hasattr(notifier, 'cleanup'):
                await notifier.cleanup()
        
        logger.info("Sistem temizlendi")
