"""
Swing yapısı analiz motoru
"""
import pandas as pd
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class SwingType(Enum):
    """Swing türleri"""
    HIGH = "high"
    LOW = "low"

@dataclass
class SwingPoint:
    """Swing noktası veri yapısı"""
    index: int
    price: float
    timestamp: str
    swing_type: SwingType
    strength: float = 0.0

class SwingEngine:
    """N-leg swing struktur analiz motoru"""
    
    def __init__(self, swing_depth: int = 5, tolerance: float = 0.001, min_swing_size: float = 0.0005):
        self.swing_depth = swing_depth
        self.tolerance = tolerance
        self.min_swing_size = min_swing_size
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.last_processed_index = -1
    
    def process_candles(self, df: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """OHLCV DataFrame'ini işleyerek swing noktalarını tespit et"""
        if len(df) < self.swing_depth * 2 + 1:
            return self.swing_highs, self.swing_lows
        
        start_idx = max(0, self.last_processed_index - self.swing_depth)
        end_idx = len(df) - self.swing_depth
        
        for i in range(start_idx, end_idx):
            self._check_swing_at_index(df, i)
        
        self.last_processed_index = end_idx
        return self.swing_highs, self.swing_lows
    
    def _check_swing_at_index(self, df: pd.DataFrame, index: int) -> None:
        """Belirtilen index'te swing var mı kontrol et"""
        if index < self.swing_depth or index >= len(df) - self.swing_depth:
            return
        
        if self._is_swing_high(df, index):
            swing_point = SwingPoint(
                index=index,
                price=df.iloc[index]['high'],
                timestamp=df.index[index].isoformat() if hasattr(df.index[index], 'isoformat') else str(df.index[index]),
                swing_type=SwingType.HIGH,
                strength=0.5
            )
            if not self._is_duplicate_swing(swing_point, self.swing_highs):
                self.swing_highs.append(swing_point)
        
        if self._is_swing_low(df, index):
            swing_point = SwingPoint(
                index=index,
                price=df.iloc[index]['low'],
                timestamp=df.index[index].isoformat() if hasattr(df.index[index], 'isoformat') else str(df.index[index]),
                swing_type=SwingType.LOW,
                strength=0.5
            )
            if not self._is_duplicate_swing(swing_point, self.swing_lows):
                self.swing_lows.append(swing_point)
    
    def _is_swing_high(self, df: pd.DataFrame, index: int) -> bool:
        """Swing high kontrolü"""
        current_high = df.iloc[index]['high']
        
        for i in range(index - self.swing_depth, index):
            if df.iloc[i]['high'] >= current_high - self.tolerance:
                return False
        
        for i in range(index + 1, index + self.swing_depth + 1):
            if df.iloc[i]['high'] >= current_high - self.tolerance:
                return False
        
        return True
    
    def _is_swing_low(self, df: pd.DataFrame, index: int) -> bool:
        """Swing low kontrolü"""
        current_low = df.iloc[index]['low']
        
        for i in range(index - self.swing_depth, index):
            if df.iloc[i]['low'] <= current_low + self.tolerance:
                return False
        
        for i in range(index + 1, index + self.swing_depth + 1):
            if df.iloc[i]['low'] <= current_low + self.tolerance:
                return False
        
        return True
    
    def _is_duplicate_swing(self, new_swing: SwingPoint, existing_swings: List[SwingPoint]) -> bool:
        """Çift swing kontrolü"""
        if not existing_swings:
            return False
        
        last_swing = existing_swings[-1]
        price_diff = abs(new_swing.price - last_swing.price)
        index_diff = abs(new_swing.index - last_swing.index)
        
        if price_diff < self.tolerance and index_diff < self.swing_depth:
            return True
        
        return False
    
    def clear_swings(self) -> None:
        """Tüm swing noktalarını temizle"""
        self.swing_highs.clear()
        self.swing_lows.clear()
        self.last_processed_index = -1
