# 🚀 Forex CHoCH Detection System

Production-grade, real-time Change-of-Character (CHoCH) detection and alerting system for forex charts.

## 🎯 Features

- **Real-time CHoCH & BOS Detection**: Advanced pattern recognition with configurable parameters
- **Multi-Broker Support**: OANDA v20, MetaTrader 5, WebSocket feeds
- **Smart Notifications**: Telegram, desktop alerts, email with rich formatting
- **Box Region Management**: Dynamic zones with TradingView webhook integration
- **Comprehensive Backtesting**: Historical data analysis with detailed reports
- **Production Ready**: Docker deployment, Redis pub/sub, PostgreSQL support
- **Rich CLI**: Beautiful command-line interface with progress tracking

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Edit `config.yaml` with your settings:

```yaml
broker:
  type: "oanda"
  environment: "practice"
  symbols: ["EUR/USD", "GBP/USD"]
  
notifications:
  telegram:
    enabled: true
    bot_token: "your_bot_token"
    chat_id: "your_chat_id"
```

### Running

```bash
# Run demo
python demo.py

# Run the system
python -m src.cli.main run

# Run backtest
python -m src.cli.main backtest EUR/USD data/sample_eurusd.csv

# Add region
python -m src.cli.main add-region EUR/USD "Support" 1.0850 1.0800

# Test data feed
python -m src.cli.main test-feed oanda
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f forex-choch-app
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 📊 Usage Examples

### Real-time Detection

```python
from src.core.config import Config
from src.core.orchestrator import TradingOrchestrator

# Load configuration
config = Config.from_file("config.yaml")

# Create and run orchestrator
orchestrator = TradingOrchestrator(config)
await orchestrator.run()
```

### Backtesting

```python
from src.pattern.choch_detector import CHoCHDetector
from src.core.config import PatternConfig

# Create detector
config = PatternConfig(swing_depth=5, tolerance=0.001)
detector = CHoCHDetector(config)

# Run backtest
results = detector.backtest("EUR/USD", df)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linting
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

**Built with ❤️ for algorithmic trading**
