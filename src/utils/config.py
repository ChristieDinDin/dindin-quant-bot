"""
Configuration management system.

Handles loading and managing configuration from YAML files and environment variables.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/database/market_data.db"
    check_same_thread: bool = False


@dataclass
class DataProviderConfig:
    """Data provider configuration."""
    default_provider: str = "yfinance"
    cache_enabled: bool = True
    default_lookback_days: int = 365
    
    # Shioaji credentials (loaded from env vars)
    shioaji_api_key: Optional[str] = None
    shioaji_secret_key: Optional[str] = None
    shioaji_simulation: bool = True


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_cash: float = 1_000_000
    # Real Taiwan round-trip (永豐 API 2折): buy 0.0285% + sell 0.3285% = 0.357%
    # + ~0.05% slippage ≈ 0.40% total; backtesting.py per-side = 0.20%
    commission: float = 0.002
    trade_on_close: bool = True

    # Paper-trading live simulation account (can differ from backtest)
    paper_equity: float = 70_000      # 7萬 TWD live simulation capital
    max_total_exposure: float = 1.0   # 100% — fully-invested limit
    min_position_pct: float = 0.05    # weakest signal → 5%
    max_position_pct: float = 0.20    # strongest signal → 20%


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    default_strategy: str = "mfi_hunter"
    
    # MFI Hunter defaults
    mfi_period: int = 16
    mfi_buy_threshold: float = 35
    mfi_sell_threshold: float = 85
    mfi_strong_buy_threshold: float = 20
    max_position_pct: float = 0.80
    normal_position_pct: float = 0.15
    strong_position_pct: float = 0.30
    
    # Divergence Hunter micro mode (1-min K, no resample)
    micro_mode_max_symbols: int = 5
    poll_interval_min: int = 5
    poll_interval_5th_min: int = 6  # Buffer for rate limit (~261 vs 270 calls/day)
    min_consecutive_bars_above: int = 10  # 1-min bars, compensates for no 5-min


@dataclass
class NotificationConfig:
    """Telegram notification configuration."""
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "logs/trading.log"
    max_bytes: int = 10_000_000  # 10MB
    backup_count: int = 5


@dataclass
class Config:
    """Main configuration class."""
    database: DatabaseConfig
    data_provider: DataProviderConfig
    backtest: BacktestConfig
    strategy: StrategyConfig
    notification: NotificationConfig
    logging: LoggingConfig

    # Environment
    environment: str = "development"  # development, production
    debug: bool = False


class ConfigManager:
    """
    Configuration manager with support for:
    - YAML config files
    - Environment variables
    - Multiple environments (dev, prod)
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config: Optional[Config] = None
    
    def load(self, environment: Optional[str] = None) -> Config:
        """
        Load configuration.
        
        Priority (highest to lowest):
        1. Environment variables
        2. Environment-specific config file (e.g., config/production.yaml)
        3. Default config file (config/default.yaml)
        
        Args:
            environment: Environment name (development, production)
                        If None, reads from ENVIRONMENT env var
        """
        # Determine environment
        if environment is None:
            environment = os.getenv('ENVIRONMENT', 'development')
        
        # Load default config
        default_config = self._load_yaml('default.yaml')
        
        # Load environment-specific config
        env_config_file = f"{environment}.yaml"
        env_config = self._load_yaml(env_config_file)
        
        # Merge configs (env overrides default)
        merged = self._merge_configs(default_config, env_config)
        
        # Override with environment variables
        merged = self._apply_env_vars(merged)
        
        # Create Config object
        self._config = self._create_config(merged, environment)
        
        return self._config
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML config file."""
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            return {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two config dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_vars(self, config: Dict) -> Dict:
        """Override config with environment variables."""
        # Database
        if 'DATABASE_PATH' in os.environ:
            config.setdefault('database', {})['path'] = os.environ['DATABASE_PATH']
        
        # Data Provider
        if 'DATA_PROVIDER' in os.environ:
            config.setdefault('data_provider', {})['default_provider'] = os.environ['DATA_PROVIDER']
        
        if 'SHIOAJI_API_KEY' in os.environ:
            config.setdefault('data_provider', {})['shioaji_api_key'] = os.environ['SHIOAJI_API_KEY']
        
        if 'SHIOAJI_SECRET_KEY' in os.environ:
            config.setdefault('data_provider', {})['shioaji_secret_key'] = os.environ['SHIOAJI_SECRET_KEY']
        
        # Strategy / Micro Mode
        if 'MICRO_MODE_MAX_SYMBOLS' in os.environ:
            config.setdefault('strategy', {})['micro_mode_max_symbols'] = int(os.environ['MICRO_MODE_MAX_SYMBOLS'])
        if 'POLL_INTERVAL' in os.environ:
            config.setdefault('strategy', {})['poll_interval_min'] = int(os.environ['POLL_INTERVAL'])
        if 'POLL_INTERVAL_5TH' in os.environ:
            config.setdefault('strategy', {})['poll_interval_5th_min'] = int(os.environ['POLL_INTERVAL_5TH'])
        if 'MIN_CONSECUTIVE_BARS_ABOVE' in os.environ:
            config.setdefault('strategy', {})['min_consecutive_bars_above'] = int(os.environ['MIN_CONSECUTIVE_BARS_ABOVE'])
        
        # Notifications (Telegram)
        if 'TELEGRAM_BOT_TOKEN' in os.environ:
            config.setdefault('notification', {})['telegram_bot_token'] = os.environ['TELEGRAM_BOT_TOKEN']
        if 'TELEGRAM_CHAT_ID' in os.environ:
            config.setdefault('notification', {})['telegram_chat_id'] = os.environ['TELEGRAM_CHAT_ID']

        # Backtest / Paper trading
        if 'INITIAL_CASH' in os.environ:
            config.setdefault('backtest', {})['initial_cash'] = float(os.environ['INITIAL_CASH'])
        if 'PAPER_EQUITY' in os.environ:
            config.setdefault('backtest', {})['paper_equity'] = float(os.environ['PAPER_EQUITY'])
        
        # Logging
        if 'LOG_LEVEL' in os.environ:
            config.setdefault('logging', {})['level'] = os.environ['LOG_LEVEL']
        
        return config
    
    def _create_config(self, data: Dict, environment: str) -> Config:
        """Create Config object from dictionary."""
        return Config(
            database=DatabaseConfig(**data.get('database', {})),
            data_provider=DataProviderConfig(**data.get('data_provider', {})),
            backtest=BacktestConfig(**data.get('backtest', {})),
            strategy=StrategyConfig(**data.get('strategy', {})),
            notification=NotificationConfig(**data.get('notification', {})),
            logging=LoggingConfig(**data.get('logging', {})),
            environment=environment,
            debug=data.get('debug', False)
        )
    
    def get(self) -> Config:
        """Get current configuration."""
        if self._config is None:
            return self.load()
        return self._config
    
    def reload(self, environment: Optional[str] = None) -> Config:
        """Reload configuration."""
        return self.load(environment)


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config(config_dir: str = "config") -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_dir: Path to config directory
        
    Returns:
        Config instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
        _config_manager.load()
    
    return _config_manager.get()


def reload_config(environment: Optional[str] = None) -> Config:
    """Reload configuration."""
    global _config_manager
    
    if _config_manager:
        return _config_manager.reload(environment)
    else:
        _config_manager = ConfigManager()
        return _config_manager.load(environment)
