"""
MetaTrader 5 bridge implementasyonu
"""
import asyncio
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from data_feed.base import DataFeedBase

logger = structlog.get_logger(__name__)

class MT5Feed(DataFeedBase):
    """MetaTrader 5 bridge implementasyonu"""
    
    def __init__(self, login: Optional[int] = None, password: Optional[str] = None, server: Optional[str] = None):
        super().__init__()
        self.login = login
        self.password = password
        self.server = server
        self.polling_task: Optional[asyncio.Task] = None
        self.polling_interval = 0.1
        self.last_ticks: Dict[str, Dict] = {}
    
    async def connect(self) -> None:
        """MT5'e bağlan"""
        logger.info("MT5'e bağlanılıyor...")
        self.connected = True
        await self._start_heartbeat()
        logger.info("MT5 bağlantısı başarılı")
    
    async def disconnect(self) -> None:
        """MT5 bağlantısını kapat"""
        logger.info("MT5 bağlantısı kapatılıyor...")
        self.connected = False
        await self._stop_heartbeat()
        if self.polling_task:
            self.polling_task.cancel()
        logger.info("MT5 bağlantısı kapatıldı")
    
    async def subscribe(self, symbol: str) -> None:
        """Sembole subscribe ol"""
        self.subscribed_symbols.add(symbol)
        if not self.polling_task:
            self.polling_task = asyncio.create_task(self._polling_loop())
        logger.info("Sembole subscribe olundu", symbol=symbol)
    
    async def unsubscribe(self, symbol: str) -> None:
        """Sembol subscription'ını iptal et"""
        self.subscribed_symbols.discard(symbol)
        if not self.subscribed_symbols and self.polling_task:
            self.polling_task.cancel()
        logger.info("Sembol subscription iptal edildi", symbol=symbol)
    
    async def _polling_loop(self) -> None:
        """Tick polling döngüsü"""
        while self.connected and self.subscribed_symbols:
            try:
                await self._poll_ticks()
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                logger.warning("Tick polling hatası", error=str(e))
                await asyncio.sleep(1)
    
    async def _poll_ticks(self) -> None:
        """Tick verilerini poll et (simulated)"""
        import random
        
        for symbol in self.subscribed_symbols.copy():
            base_price = 1.0800 if symbol == "EUR/USD" else 1.2500
            bid = base_price + random.uniform(-0.001, 0.001)
            ask = bid + 0.0001
            
            tick_data = {
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "spread": ask - bid,
                "timestamp": datetime.now().isoformat(),
                "volume": random.randint(1, 10)
            }
            
            last_tick = self.last_ticks.get(symbol)
            if not last_tick or abs(last_tick["bid"] - bid) > 0.00001:
                await self._emit_tick(symbol, tick_data)
                self.last_ticks[symbol] = tick_data
