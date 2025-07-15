"""
Telegram bildirim servisi
"""
import asyncio
from typing import Optional, Dict, Any
import aiohttp
import structlog
from datetime import datetime

from notifier.base import NotifierBase

logger = structlog.get_logger(__name__)

class TelegramNotifier(NotifierBase):
    """Telegram bot kullanarak bildirim gönderen sınıf"""
    
    def __init__(self, bot_token: str, chat_id: str):
        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_message_time = 0
        self.min_interval = 1.0
        
        self.emoji_map = {
            "choch": "🔄",
            "bos": "💥",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
    
    async def initialize(self) -> None:
        """Telegram bot'u başlat"""
        try:
            self.session = aiohttp.ClientSession()
            await self._validate_bot()
            self.initialized = True
            logger.info("Telegram notifier başlatıldı")
        except Exception as e:
            logger.error("Telegram notifier başlatma hatası", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """Temizlik işlemleri"""
        if self.session:
            await self.session.close()
    
    async def send_notification(self, message: str, alert_type: str = "info", **kwargs) -> bool:
        """Telegram'a bildirim gönder"""
        if not self.initialized:
            return False
        
        try:
            await self._rate_limit_check()
            formatted_message = self._format_message(message, alert_type)
            success = await self._send_to_telegram(formatted_message)
            
            if success:
                self.sent_count += 1
            else:
                self.failed_count += 1
            
            return success
        except Exception as e:
            self.failed_count += 1
            logger.error("Telegram mesaj gönderme hatası", error=str(e))
            return False
    
    async def _validate_bot(self) -> None:
        """Bot token'ını doğrula"""
        url = f"{self.base_url}/getMe"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Bot token doğrulaması başarısız: {response.status}")
            
            data = await response.json()
            if not data.get("ok"):
                raise Exception(f"Bot API hatası: {data.get('description')}")
    
    async def _rate_limit_check(self) -> None:
        """Rate limiting kontrolü"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_message_time
        
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        self.last_message_time = time.time()
    
    def _format_message(self, message: str, alert_type: str) -> str:
        """Mesajı formatla"""
        emoji = self.emoji_map.get(alert_type, "📱")
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"{emoji} *{alert_type.upper()}* | {timestamp}\n\n{message}"
    
    async def _send_to_telegram(self, message: str) -> bool:
        """Telegram API'ye mesaj gönder"""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("ok", False)
                return False
        except Exception as e:
            logger.error("Telegram request hatası", error=str(e))
            return False
