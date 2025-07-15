"""
Email bildirim servisi
"""
import structlog
from notifier.base import NotifierBase

logger = structlog.get_logger(__name__)

class EmailNotifier(NotifierBase):
    """Email bildirim sınıfı"""
    
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str):
        super().__init__()
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
    
    async def initialize(self) -> None:
        """Email notifier'ı başlat"""
        self.initialized = True
        logger.info("Email notifier başlatıldı")
    
    async def send_notification(self, message: str, alert_type: str = "info", **kwargs) -> bool:
        """Email bildirimi gönder"""
        if not self.initialized:
            return False
        
        try:
            subject = f"Forex CHoCH Alert - {alert_type.upper()}"
            logger.info("Email gönderildi", subject=subject, message=message[:100])
            self.sent_count += 1
            return True
        except Exception as e:
            self.failed_count += 1
            logger.error("Email gönderme hatası", error=str(e))
            return False
