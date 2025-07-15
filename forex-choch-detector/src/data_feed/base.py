"""
Data feed için temel sınıf - Strategy pattern implementasyonu
"""
from abc import ABC, abstractmethod
from typing import Dict, Callable, Optional, Any
import asyncio
import structlog

logger = structlog.get_logger(__name__)

class DataFeedBase(ABC):
    """
    Tüm data feed'ler için temel sınıf
    """
    
    def __init__(self):
        self.connected = False
        self.subscribed_symbols = set()
        
        # Event callbacks
        self.on_tick: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_connection_status: Optional[Callable] = None
        
        # Heartbeat
        self.heartbeat_interval = 30
        self.last_heartbeat = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def connect(self) -> None:
        """Broker'a bağlan"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Bağlantıyı kapat"""
        pass
    
    @abstractmethod
    async def subscribe(self, symbol: str) -> None:
        """Sembole subscribe ol"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbol: str) -> None:
        """Sembol subscription'ını iptal et"""
        pass
    
    async def _emit_tick(self, symbol: str, tick_data: Dict[str, Any]) -> None:
        """Tick event'ini emit et"""
        if self.on_tick:
            try:
                await self.on_tick(symbol, tick_data)
            except Exception as e:
                logger.error("Tick callback hatası", symbol=symbol, error=str(e))
    
    async def _emit_error(self, error: Exception) -> None:
        """Error event'ini emit et"""
        if self.on_error:
            try:
                await self.on_error(error)
            except Exception as e:
                logger.error("Error callback hatası", error=str(e))
    
    async def _start_heartbeat(self) -> None:
        """Heartbeat görevini başlat"""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat döngüsü"""
        while self.connected:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.warning("Heartbeat hatası", error=str(e))
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self) -> None:
        """Heartbeat gönder - alt sınıflar override edebilir"""
        import time
        self.last_heartbeat = time.time()
    
    async def _stop_heartbeat(self) -> None:
        """Heartbeat görevini durdur"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
