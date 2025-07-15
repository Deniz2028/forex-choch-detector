"""
CHoCH ve BOS tespit motoru
"""
import pandas as pd
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import structlog
from datetime import datetime

# Relative import'ları absolute yap
from pattern.swing_engine import SwingEngine, SwingPoint, SwingType
from core.config import PatternConfig

logger = structlog.get_logger(__name__)

class TrendDirection(Enum):
    """Trend yönü"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"

class PatternType(Enum):
    """Pattern türleri"""
    CHOCH = "choch"
    BOS = "bos"

@dataclass
class PatternEvent:
    """Pattern event veri yapısı"""
    pattern_type: PatternType
    symbol: str
    direction: TrendDirection
    price: float
    timestamp: str
    confidence: float
    swing_points: List[SwingPoint]
    metadata: Dict[str, Any]

class CHoCHDetector:
    """CHoCH ve BOS tespit motoru"""
    
    def __init__(self, config: PatternConfig):
        self.config = config
        self.swing_engine = SwingEngine(
            swing_depth=config.swing_depth,
            tolerance=config.tolerance,
            min_swing_size=config.min_swing_size
        )
        self.symbol_data: Dict[str, pd.DataFrame] = {}
        self.current_trends: Dict[str, TrendDirection] = {}
        self.on_choch: Optional[Callable] = None
        self.on_bos: Optional[Callable] = None
        self.on_abort: Optional[Callable] = None
        self.pattern_history: List[PatternEvent] = []
    
    async def process_tick(self, symbol: str, tick_data: Dict[str, Any]) -> None:
        """Yeni tick verisini işle"""
        try:
            await self._update_ohlcv_from_tick(symbol, tick_data)
            await self._analyze_patterns(symbol)
        except Exception as e:
            logger.error("Tick işleme hatası", symbol=symbol, error=str(e))
    
    async def _update_ohlcv_from_tick(self, symbol: str, tick_data: Dict[str, Any]) -> None:
        """Tick verisinden OHLCV bar'ı güncelle"""
        if symbol not in self.symbol_data:
            self.symbol_data[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        df = self.symbol_data[symbol]
        mid_price = (tick_data['bid'] + tick_data['ask']) / 2
        timestamp = pd.to_datetime(tick_data['timestamp'])
        bar_time = timestamp.floor('T')
        
        if len(df) > 0 and df.index[-1] == bar_time:
            df.iloc[-1, df.columns.get_loc('high')] = max(df.iloc[-1]['high'], mid_price)
            df.iloc[-1, df.columns.get_loc('low')] = min(df.iloc[-1]['low'], mid_price)
            df.iloc[-1, df.columns.get_loc('close')] = mid_price
            df.iloc[-1, df.columns.get_loc('volume')] += tick_data.get('volume', 1)
        else:
            new_bar = pd.DataFrame({
                'open': [mid_price],
                'high': [mid_price],
                'low': [mid_price],
                'close': [mid_price],
                'volume': [tick_data.get('volume', 1)]
            }, index=[bar_time])
            self.symbol_data[symbol] = pd.concat([df, new_bar])
        
        if len(self.symbol_data[symbol]) > 1000:
            self.symbol_data[symbol] = self.symbol_data[symbol].tail(1000)
    
    async def _analyze_patterns(self, symbol: str) -> None:
        """Pattern analizi yap"""
        if symbol not in self.symbol_data:
            return
        
        df = self.symbol_data[symbol]
        if len(df) < self.config.swing_depth * 4:
            return
        
        swing_highs, swing_lows = self.swing_engine.process_candles(df)
        await self._detect_choch(symbol, swing_highs, swing_lows)
        await self._detect_bos(symbol, swing_highs, swing_lows)
    
    async def _detect_choch(self, symbol: str, swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]) -> None:
        """CHoCH tespiti"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return
        
        current_trend = self.current_trends.get(symbol, TrendDirection.SIDEWAYS)
        
        if current_trend == TrendDirection.BEARISH:
            recent_highs = swing_highs[-2:]
            if len(recent_highs) >= 2 and recent_highs[1].price > recent_highs[0].price:
                await self._emit_choch(symbol, TrendDirection.BULLISH, recent_highs, recent_highs[1].price)
                self.current_trends[symbol] = TrendDirection.BULLISH
        elif current_trend == TrendDirection.BULLISH:
            recent_lows = swing_lows[-2:]
            if len(recent_lows) >= 2 and recent_lows[1].price < recent_lows[0].price:
                await self._emit_choch(symbol, TrendDirection.BEARISH, recent_lows, recent_lows[1].price)
                self.current_trends[symbol] = TrendDirection.BEARISH
    
    async def _detect_bos(self, symbol: str, swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]) -> None:
        """BOS tespiti"""
        pass
    
    async def _emit_choch(self, symbol: str, direction: TrendDirection, swing_points: List[SwingPoint], price: float) -> None:
        """CHoCH event'ini emit et"""
        event = PatternEvent(
            pattern_type=PatternType.CHOCH,
            symbol=symbol,
            direction=direction,
            price=price,
            timestamp=datetime.now().isoformat(),
            confidence=0.8,
            swing_points=swing_points,
            metadata={}
        )
        self.pattern_history.append(event)
        
        if self.on_choch:
            await self.on_choch(symbol, {
                "direction": direction.value,
                "price": price,
                "timestamp": event.timestamp,
                "confidence": event.confidence
            })
    
    def backtest(self, symbol: str, df: pd.DataFrame) -> List[PatternEvent]:
        """Backtest yap"""
        logger.info("Backtest başlatılıyor", symbol=symbol)
        self.symbol_data[symbol] = df.copy()
        self.current_trends[symbol] = TrendDirection.SIDEWAYS
        self.pattern_history.clear()
        swing_highs, swing_lows = self.swing_engine.process_candles(df)
        return self.pattern_history.copy()
