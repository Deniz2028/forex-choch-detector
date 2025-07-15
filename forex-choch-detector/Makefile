# Forex CHoCH Detection System Makefile

.PHONY: help install test run

help:
	@echo "🚀 Forex CHoCH Detection System"
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  run         - Run the application"
	@echo "  docker-run  - Run with Docker"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	python -m src.cli.main run

docker-run:
	docker-compose up -d

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
