"""
Yapılandırma yöneticisi - pydantic ile type-safe config handling
"""
import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import yaml
from pathlib import Path

class BrokerConfig(BaseModel):
    """Broker bağlantı konfigürasyonu"""
    type: str = Field(..., description="Broker türü: oanda, mt5, websocket")
    api_key: Optional[str] = None
    account_id: Optional[str] = None
    environment: str = "practice"  # practice veya live
    symbols: List[str] = Field(default_factory=list)
    
class TelegramConfig(BaseModel):
    """Telegram bot konfigürasyonu"""
    bot_token: str = Field(..., description="Bot token")
    chat_id: str = Field(..., description="Hedef chat ID")
    enabled: bool = True

class NotificationConfig(BaseModel):
    """Bildirim ayarları"""
    telegram: Optional[TelegramConfig] = None
    email_enabled: bool = False
    desktop_enabled: bool = True
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

class PatternConfig(BaseModel):
    """Pattern detection ayarları"""
    swing_depth: int = Field(default=5, ge=3, le=20)
    tolerance: float = Field(default=0.001, ge=0.0001, le=0.01)
    min_swing_size: float = Field(default=0.0005, ge=0.0001)
    
class Config(BaseModel):
    """Ana konfigürasyon sınıfı"""
    broker: BrokerConfig
    notifications: NotificationConfig
    pattern: PatternConfig
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379"
    database_url: Optional[str] = None
    
    @classmethod
    def from_file(cls, config_path: str = "config.yaml") -> "Config":
        """YAML dosyasından config yükle"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config dosyası bulunamadı: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        # Environment değişkenleri ile override
        cls._override_with_env(data)
        return cls(**data)
    
    @staticmethod
    def _override_with_env(data: Dict[str, Any]) -> None:
        """Environment değişkenleri ile override işlemi"""
        env_mappings = {
            'OANDA_API_KEY': ['broker', 'api_key'],
            'OANDA_ACCOUNT_ID': ['broker', 'account_id'],
            'TELEGRAM_BOT_TOKEN': ['notifications', 'telegram', 'bot_token'],
            'TELEGRAM_CHAT_ID': ['notifications', 'telegram', 'chat_id'],
            'REDIS_URL': ['redis_url'],
            'DATABASE_URL': ['database_url']
        }
        
        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                current = data
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[path[-1]] = value
