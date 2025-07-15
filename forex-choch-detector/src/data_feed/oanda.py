"""
OANDA v20 API streaming data feed implementasyonu
"""
import asyncio
import json
from typing import Dict, Any, Optional
import aiohttp
import structlog
from datetime import datetime

from data_feed.base import DataFeedBase

logger = structlog.get_logger(__name__)

class OandaFeed(DataFeedBase):
    """
    OANDA v20 streaming API implementasyonu
    """
    
    def __init__(self, api_key: str, account_id: str, environment: str = "practice"):
        super().__init__()
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment
        
        # API endpoints
        base_url = "https://api-fxpractice.oanda.com" if environment == "practice" else "https://api-fxtrade.oanda.com"
        self.rest_url = f"{base_url}/v3"
        self.stream_url = f"{base_url.replace('api', 'stream')}/v3"
        
        # Session ve streaming
        self.session: Optional[aiohttp.ClientSession] = None
        self.stream_response: Optional[aiohttp.ClientResponse] = None
        self.stream_task: Optional[asyncio.Task] = None
        
        # Headers
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339"
        }
    
    async def connect(self) -> None:
        """OANDA API'ye bağlan"""
        try:
            logger.info("OANDA'ya bağlanılıyor...")
            
            # Session oluştur
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=self.headers
            )
            
            # Hesap bilgilerini kontrol et
            await self._validate_account()
            
            self.connected = True
            await self._start_heartbeat()
            
            logger.info("OANDA bağlantısı başarılı")
            
        except Exception as e:
            logger.error("OANDA bağlantı hatası", error=str(e))
            await self.disconnect()
            raise
    
    async def disconnect(self) -> None:
        """OANDA bağlantısını kapat"""
        logger.info("OANDA bağlantısı kapatılıyor...")
        
        self.connected = False
        await self._stop_heartbeat()
        
        # Stream'i kapat
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        
        if self.stream_response:
            self.stream_response.close()
        
        if self.session:
            await self.session.close()
        
        logger.info("OANDA bağlantısı kapatıldı")
    
    async def subscribe(self, symbol: str) -> None:
        """Sembole subscribe ol"""
        if not self.connected:
            raise RuntimeError("Bağlantı kurulmamış")
        
        # OANDA formatına çevir (EUR/USD -> EUR_USD)
        oanda_symbol = symbol.replace("/", "_")
        self.subscribed_symbols.add(oanda_symbol)
        
        # Streaming başlat
        await self._start_streaming()
        
        logger.info("Sembole subscribe olundu", symbol=symbol)
    
    async def unsubscribe(self, symbol: str) -> None:
        """Sembol subscription'ını iptal et"""
        oanda_symbol = symbol.replace("/", "_")
        self.subscribed_symbols.discard(oanda_symbol)
        
        # Eğer hiç symbol kalmadıysa streaming'i durdur
        if not self.subscribed_symbols and self.stream_task:
            self.stream_task.cancel()
        
        logger.info("Sembol subscription iptal edildi", symbol=symbol)
    
    async def _validate_account(self) -> None:
        """Hesap bilgilerini doğrula"""
        url = f"{self.rest_url}/accounts/{self.account_id}"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Hesap doğrulaması başarısız: {response.status}")
            
            data = await response.json()
            account_info = data.get("account", {})
            
            logger.info("Hesap doğrulandı", 
                       currency=account_info.get("currency"),
                       balance=account_info.get("balance"))
    
    async def _start_streaming(self) -> None:
        """Price streaming başlat"""
        if self.stream_task or not self.subscribed_symbols:
            return
        
        self.stream_task = asyncio.create_task(self._stream_prices())
    
    async def _stream_prices(self) -> None:
        """Price stream döngüsü"""
        instruments = ",".join(self.subscribed_symbols)
        url = f"{self.stream_url}/accounts/{self.account_id}/pricing/stream"
        
        params = {
            "instruments": instruments,
            "snapshot": "true"
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Streaming başarısız: {response.status}")
                
                self.stream_response = response
                
                async for line in response.content:
                    if not self.connected:
                        break
                    
                    try:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        
                        data = json.loads(line)
                        await self._process_stream_data(data)
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.warning("Stream data işleme hatası", error=str(e))
        
        except Exception as e:
            logger.error("Price streaming hatası", error=str(e))
            await self._emit_error(e)
    
    async def _process_stream_data(self, data: Dict[str, Any]) -> None:
        """Stream verisini işle"""
        msg_type = data.get("type")
        
        if msg_type == "PRICE":
            await self._process_price_data(data)
        elif msg_type == "HEARTBEAT":
            await self._process_heartbeat(data)
    
    async def _process_price_data(self, data: Dict[str, Any]) -> None:
        """Price verisini işle ve tick event'i emit et"""
        instrument = data.get("instrument")
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        if not bids or not asks:
            return
        
        # En iyi bid/ask al
        best_bid = float(bids[0].get("price", 0))
        best_ask = float(asks[0].get("price", 0))
        
        # Tick verisi oluştur
        tick_data = {
            "symbol": instrument.replace("_", "/"),
            "bid": best_bid,
            "ask": best_ask,
            "spread": best_ask - best_bid,
            "timestamp": datetime.now().isoformat(),
            "raw_data": data
        }
        
        await self._emit_tick(instrument, tick_data)
    
    async def _process_heartbeat(self, data: Dict[str, Any]) -> None:
        """Heartbeat mesajını işle"""
        import time
        self.last_heartbeat = time.time()
        logger.debug("OANDA heartbeat alındı", time=data.get("time"))
