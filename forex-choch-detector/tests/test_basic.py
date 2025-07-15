"""
Basic test file
"""
import pytest
import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.config import PatternConfig
from pattern.choch_detector import CHoCHDetector
from region.box_region import BoxRegionManager

def test_pattern_config():
    """Test pattern configuration"""
    config = PatternConfig(
        swing_depth=5,
        tolerance=0.001,
        min_swing_size=0.0005
    )
    
    assert config.swing_depth == 5
    assert config.tolerance == 0.001
    assert config.min_swing_size == 0.0005

def test_choch_detector():
    """Test CHoCH detector initialization"""
    config = PatternConfig()
    detector = CHoCHDetector(config)
    
    assert detector.config.swing_depth == 5
    assert len(detector.pattern_history) == 0

def test_box_region_manager():
    """Test box region manager"""
    manager = BoxRegionManager()
    
    region_id = manager.add_region(
        symbol="EUR/USD",
        name="Test Zone",
        upper_bound=1.0850,
        lower_bound=1.0800
    )
    
    assert region_id is not None
    assert len(manager.regions["EUR/USD"]) == 1
    
    regions = manager.get_regions("EUR/USD")
    assert len(regions) == 1
    assert regions[0].name == "Test Zone"

@pytest.mark.asyncio
async def test_region_hit():
    """Test region hit detection"""
    manager = BoxRegionManager()
    
    manager.add_region("EUR/USD", "Test Zone", 1.0850, 1.0800)
    
    hit_detected = False
    async def on_hit(symbol, data):
        nonlocal hit_detected
        hit_detected = True
    
    manager.on_region_hit = on_hit
    
    # Price inside region
    tick_data = {"bid": 1.0824, "ask": 1.0826}
    await manager.check_regions("EUR/USD", tick_data)
    
    assert hit_detected
