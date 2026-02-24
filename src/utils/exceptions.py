"""
Custom exceptions for the trading bot.

Provides domain-specific exceptions for better error handling.
"""


class TradingBotException(Exception):
    """Base exception for all trading bot errors."""
    pass


# Data-related exceptions
class DataException(TradingBotException):
    """Base exception for data-related errors."""
    pass


class DataProviderException(DataException):
    """Error from data provider (yfinance, Shioaji, etc.)."""
    pass


class DataNotFoundException(DataException):
    """Requested data not found."""
    pass


class DataValidationException(DataException):
    """Data failed validation checks."""
    pass


# Strategy-related exceptions
class StrategyException(TradingBotException):
    """Base exception for strategy errors."""
    pass


class StrategyNotFoundError(StrategyException):
    """Strategy not found in registry."""
    pass


class InvalidStrategyParameterError(StrategyException):
    """Invalid parameter provided to strategy."""
    pass


# Backtesting exceptions
class BacktestException(TradingBotException):
    """Base exception for backtesting errors."""
    pass


class InsufficientDataError(BacktestException):
    """Not enough data to run backtest."""
    pass


# Database exceptions
class DatabaseException(TradingBotException):
    """Base exception for database errors."""
    pass


class DatabaseConnectionError(DatabaseException):
    """Failed to connect to database."""
    pass


# Configuration exceptions
class ConfigurationException(TradingBotException):
    """Base exception for configuration errors."""
    pass


class InvalidConfigurationError(ConfigurationException):
    """Configuration is invalid or incomplete."""
    pass


# Trading exceptions (for live trading)
class TradingException(TradingBotException):
    """Base exception for live trading errors."""
    pass


class OrderExecutionError(TradingException):
    """Failed to execute order."""
    pass


class InsufficientFundsError(TradingException):
    """Not enough funds to execute trade."""
    pass


class RiskLimitExceededError(TradingException):
    """Trade would exceed risk limits."""
    pass
