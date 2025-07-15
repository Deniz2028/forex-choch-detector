"""
Bildirim servisleri için temel sınıf
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class NotifierBase(ABC):
    """Tüm bildirim servisleri için temel sınıf"""
    
    def __init__(self):
        self.initialized = False
        self.sent_count = 0
        self.failed_count = 0
    
    @abstractmethod
    async def initialize(self) -> None:
        """Notifier'ı başlat"""
        pass
    
    @abstractmethod
    async def send_notification(self, message: str, alert_type: str = "info", **kwargs) -> bool:
        """Bildirim gönder"""
        pass
    
    async def cleanup(self) -> None:
        """Temizlik işlemleri"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri al"""
        return {
            "initialized": self.initialized,
            "sent_count": self.sent_count,
            "failed_count": self.failed_count
        }
