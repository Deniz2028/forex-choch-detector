"""
Box region yönetim sistemi
"""
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class BoxRegion:
    """Box region veri yapısı"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    name: str = ""
    upper_bound: float = 0.0
    lower_bound: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True
    region_type: str = "static"
    metadata: Dict[str, Any] = field(default_factory=dict)
    hit_count: int = 0
    last_hit: Optional[str] = None
    
    def contains_price(self, price: float) -> bool:
        """Fiyatın region içinde olup olmadığını kontrol et"""
        return self.lower_bound <= price <= self.upper_bound
    
    def get_statistics(self) -> Dict[str, Any]:
        """Region istatistikleri"""
        return {
            "hit_count": self.hit_count,
            "last_hit": self.last_hit,
            "is_active": self.is_active
        }

class BoxRegionManager:
    """Box region yönetim sınıfı"""
    
    def __init__(self):
        self.regions: Dict[str, List[BoxRegion]] = {}
        self.on_region_hit: Optional[Callable] = None
        self.on_region_break: Optional[Callable] = None
        self.hit_history: List[Dict[str, Any]] = []
    
    def add_region(self, symbol: str, name: str, upper_bound: float, lower_bound: float, 
                   region_type: str = "static", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Yeni region ekle"""
        if symbol not in self.regions:
            self.regions[symbol] = []
        
        region = BoxRegion(
            symbol=symbol,
            name=name,
            upper_bound=max(upper_bound, lower_bound),
            lower_bound=min(upper_bound, lower_bound),
            region_type=region_type,
            metadata=metadata or {}
        )
        
        self.regions[symbol].append(region)
        logger.info("Yeni region eklendi", symbol=symbol, name=name)
        return region.id
    
    def get_regions(self, symbol: str, active_only: bool = True) -> List[BoxRegion]:
        """Symbol'ün region'larını al"""
        if symbol not in self.regions:
            return []
        
        regions = self.regions[symbol]
        if active_only:
            regions = [r for r in regions if r.is_active]
        return regions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Tüm istatistikleri al"""
        stats = {}
        for symbol, regions in self.regions.items():
            stats[symbol] = {
                "total_regions": len(regions),
                "active_regions": len([r for r in regions if r.is_active]),
                "total_hits": sum(r.hit_count for r in regions)
            }
        return stats
    
    async def check_regions(self, symbol: str, tick_data: Dict[str, Any]) -> None:
        """Region kontrolü yap"""
        if symbol not in self.regions:
            return
        
        if 'bid' in tick_data and 'ask' in tick_data:
            current_price = (tick_data['bid'] + tick_data['ask']) / 2
        else:
            return
        
        for region in self.get_regions(symbol):
            if region.contains_price(current_price):
                region.hit_count += 1
                region.last_hit = datetime.now().isoformat()
                
                if self.on_region_hit:
                    await self.on_region_hit(symbol, {
                        "region_id": region.id,
                        "region_name": region.name,
                        "price": current_price,
                        "hit_count": region.hit_count
                    })
