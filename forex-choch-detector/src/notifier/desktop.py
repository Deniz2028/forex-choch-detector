"""
Desktop bildirim servisi
"""
import sys
import structlog
from notifier.base import NotifierBase

logger = structlog.get_logger(__name__)

class DesktopNotifier(NotifierBase):
    """Desktop bildirim sınıfı"""
    
    def __init__(self):
        super().__init__()
        self.platform = sys.platform
    
    async def initialize(self) -> None:
        """Desktop notifier'ı başlat"""
        self.initialized = True
        logger.info("Desktop notifier başlatıldı", platform=self.platform)
    
    async def send_notification(self, message: str, alert_type: str = "info", **kwargs) -> bool:
        """Desktop bildirimi gönder"""
        if not self.initialized:
            return False
        
        try:
            title = f"Forex CHoCH - {alert_type.upper()}"
            logger.info("Desktop bildirimi gönderildi", title=title, message=message)
            self.sent_count += 1
            return True
        except Exception as e:
            self.failed_count += 1
            logger.error("Desktop bildirim hatası", error=str(e))
            return False
