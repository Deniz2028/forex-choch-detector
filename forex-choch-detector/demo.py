# demo.py dosyasını bu şekilde değiştir:
#!/usr/bin/env python3
"""
🚀 Forex CHoCH Detection System - Demo Script
Bu script sistemi hızlı test etmek için kullanılır.
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add src to path - düzeltilmiş version
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Şimdi import'lar çalışacak
from core.config import PatternConfig
from pattern.choch_detector import CHoCHDetector
from data_feed.mt5 import MT5Feed
from region.box_region import BoxRegionManager

def generate_sample_data():
    """Sample forex data üret"""
    print("📊 Generating sample data...")
    
    np.random.seed(42)
    bars = 200
    
    # Trending data with some CHoCH patterns
    prices = []
    base_price = 1.0800
    
    for i in range(bars):
        # Add some trending behavior
        if i < 50:
            drift = 0.0002  # Uptrend
        elif i < 100:
            drift = -0.0001  # Downtrend
        elif i < 150:
            drift = 0.0003  # Strong uptrend
        else:
            drift = -0.0002  # Correction
        
        base_price += drift + np.random.normal(0, 0.0005)
        prices.append(base_price)
    
    # Create OHLCV data
    time_index = pd.date_range(
        start=datetime.now() - timedelta(hours=bars), 
        periods=bars, 
        freq='H'
    )
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(0, 0.0008) for p in prices],
        'low': [p - np.random.uniform(0, 0.0008) for p in prices],
        'close': prices,
        'volume': np.random.randint(100, 1000, bars)
    }, index=time_index)
    
    return df

async def demo_backtest():
    """Demo backtest çalıştır"""
    print("🎯 Running CHoCH Detection Demo...")
    
    # Generate sample data
    df = generate_sample_data()
    
    # Configure pattern detection
    pattern_config = PatternConfig(
        swing_depth=5,
        tolerance=0.001,
        min_swing_size=0.0005
    )
    
    # Create detector
    detector = CHoCHDetector(pattern_config)
    
    # Run backtest
    print("🔍 Analyzing patterns...")
    results = detector.backtest("EUR/USD", df)
    
    # Display results
    print(f"\n📈 Analysis Results:")
    print(f"   Total bars analyzed: {len(df)}")
    print(f"   Patterns detected: {len(results)}")
    
    if results:
        choch_count = len([r for r in results if r.pattern_type.value == 'choch'])
        bos_count = len([r for r in results if r.pattern_type.value == 'bos'])
        
        print(f"   🔄 CHoCH patterns: {choch_count}")
        print(f"   💥 BOS patterns: {bos_count}")
        
        print(f"\n📊 Recent Patterns:")
        for i, result in enumerate(results[-3:], 1):
            emoji = "🔄" if result.pattern_type.value == "choch" else "💥"
            direction = "📈" if result.direction.value == "bullish" else "📉"
            print(f"   {i}. {emoji} {result.pattern_type.value.upper()} {direction} {result.direction.value}")
            print(f"      Price: {result.price:.5f} | Confidence: {result.confidence:.1%}")
    else:
        print("   No patterns detected. Try adjusting parameters.")
    
    return results

async def demo_region_management():
    """Demo region management"""
    print("\n📍 Region Management Demo...")
    
    # Create region manager
    manager = BoxRegionManager()
    
    # Add some regions
    regions = [
        ("EUR/USD", "Support Zone 1", 1.0850, 1.0800),
        ("EUR/USD", "Resistance Zone 1", 1.0900, 1.0880),
        ("EUR/USD", "Support Zone 2", 1.0750, 1.0720),
        ("GBP/USD", "Key Level", 1.2500, 1.2480)
    ]
    
    for symbol, name, upper, lower in regions:
        region_id = manager.add_region(symbol, name, upper, lower)
        print(f"   ✅ Added: {name} ({lower:.4f} - {upper:.4f})")
    
    # Test region checking
    print("\n🎯 Testing region hits...")
    
    # Simulate some price hits
    test_prices = [
        ("EUR/USD", 1.0825),  # Should hit Support Zone 1
        ("EUR/USD", 1.0890),  # Should hit Resistance Zone 1
        ("EUR/USD", 1.0735),  # Should hit Support Zone 2
        ("GBP/USD", 1.2490),  # Should hit Key Level
        ("EUR/USD", 1.0950),  # Should not hit any region
    ]
    
    hit_count = 0
    async def on_region_hit(symbol, hit_data):
        nonlocal hit_count
        hit_count += 1
        print(f"   🎯 HIT: {hit_data['region_name']} at {hit_data['price']:.4f}")
    
    manager.on_region_hit = on_region_hit
    
    for symbol, price in test_prices:
        tick_data = {"bid": price - 0.0001, "ask": price + 0.0001}
        await manager.check_regions(symbol, tick_data)
    
    print(f"\n📊 Region Statistics:")
    stats = manager.get_statistics()
    for symbol, stat in stats.items():
        print(f"   {symbol}: {stat['total_regions']} regions, {stat['total_hits']} hits")

async def demo_data_feed():
    """Demo data feed (simulated)"""
    print("\n📡 Data Feed Demo...")
    
    # Create MT5 feed (simulated)
    feed = MT5Feed()
    
    # Set up callback
    tick_count = 0
    async def on_tick(symbol, tick_data):
        nonlocal tick_count
        tick_count += 1
        if tick_count <= 5:  # Show first 5 ticks
            print(f"   📊 {symbol}: {tick_data['bid']:.5f}/{tick_data['ask']:.5f}")
    
    feed.on_tick = on_tick
    
    # Connect and subscribe
    await feed.connect()
    await feed.subscribe("EUR/USD")
    
    print("   🔄 Receiving simulated ticks...")
    
    # Let it run for a few seconds
    await asyncio.sleep(2)
    
    # Disconnect
    await feed.disconnect()
    
    print(f"   ✅ Received {tick_count} ticks")

async def main():
    """Ana demo fonksiyonu"""
    print("🚀 Forex CHoCH Detection System - Demo")
    print("=" * 50)
    
    try:
        # Run demos
        await demo_backtest()
        await demo_region_management()
        await demo_data_feed()
        
        print("\n🎉 Demo completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Edit config.yaml with your credentials")
        print("   2. Run: python -m src.cli.main run")
        print("   3. Or run full backtest: python -m src.cli.main backtest EUR/USD data/sample_eurusd.csv")
        
    except Exception as e:
        print(f"\n❌ Demo error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
