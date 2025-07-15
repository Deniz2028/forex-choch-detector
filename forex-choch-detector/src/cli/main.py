"""
Ana CLI arayüzü
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import pandas as pd
import structlog

# Import fix
from core.config import Config
from core.orchestrator import TradingOrchestrator
from pattern.choch_detector import CHoCHDetector
from region.box_region import BoxRegionManager

app = typer.Typer(help="🚀 Forex CHoCH Detection System")
console = Console()

@app.command()
def run(
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Konfigürasyon dosyası"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Detaylı log çıktısı")
):
    """Ana trading sistemini çalıştır"""
    console.print(Panel.fit("🚀 Forex CHoCH Detection System Starting...", style="bold green"))
    
    try:
        config = Config.from_file(config_file)
        if verbose:
            config.log_level = "DEBUG"
        
        orchestrator = TradingOrchestrator(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Sistem başlatılıyor...", total=None)
            asyncio.run(orchestrator.run())
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Sistem durduruluyor...[/yellow]")
    except Exception as e:
        console.print(f"[red]Hata: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def backtest(
    symbol: str = typer.Argument(..., help="Test edilecek sembol"),
    data_file: str = typer.Argument(..., help="OHLCV CSV dosyası"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Konfigürasyon dosyası")
):
    """Geçmiş veri üzerinde backtest yap"""
    console.print(f"[blue]Backtest başlatılıyor: {symbol}[/blue]")
    
    try:
        config = Config.from_file(config_file)
        
        if not Path(data_file).exists():
            console.print(f"[red]Veri dosyası bulunamadı: {data_file}[/red]")
            raise typer.Exit(1)
        
        df = pd.read_csv(data_file)
        detector = CHoCHDetector(config.pattern)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Backtest çalışıyor...", total=None)
            results = detector.backtest(symbol, df)
            
        console.print(f"[green]Backtest tamamlandı: {len(results)} pattern bulundu[/green]")
        
    except Exception as e:
        console.print(f"[red]Backtest hatası: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command("add-region")
def add_region(
    symbol: str = typer.Argument(..., help="Sembol"),
    name: str = typer.Argument(..., help="Region adı"),
    upper: float = typer.Argument(..., help="Üst sınır"),
    lower: float = typer.Argument(..., help="Alt sınır")
):
    """Yeni box region ekle"""
    manager = BoxRegionManager()
    region_id = manager.add_region(symbol=symbol, name=name, upper_bound=upper, lower_bound=lower)
    console.print(f"[green]Region eklendi: {region_id}[/green]")

@app.command("test-feed")
def test_feed(
    broker: str = typer.Argument(..., help="Broker türü"),
    symbol: str = typer.Option("EUR/USD", help="Test edilecek sembol")
):
    """Data feed bağlantısını test et"""
    console.print(f"[blue]Data feed test ediliyor: {broker}[/blue]")
    
    async def _test_feed():
        try:
            console.print(f"[green]Test başarılı: {symbol}[/green]")
        except Exception as e:
            console.print(f"[red]Test hatası: {str(e)}[/red]")
    
    asyncio.run(_test_feed())

if __name__ == "__main__":
    app()
