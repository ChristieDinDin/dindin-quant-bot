"""
Strategy registry for managing and discovering available strategies.

This provides a centralized way to:
- Register new strategies
- Discover available strategies
- Create strategy instances with parameters
- Support plugin architecture for custom strategies
"""
from typing import Dict, Type, Optional, Any, List
import inspect

from .base import Strategy
from .mfi_hunter import MfiHunterStrategy
from .rsi_mfi_consensus import RsiMfiConsensusStrategy


class StrategyRegistry:
    """
    Central registry for all trading strategies.
    
    Benefits:
    - Decouples strategy creation from usage
    - Enables dynamic strategy loading
    - Supports configuration-driven strategy selection
    - Makes testing easier
    """
    
    def __init__(self):
        self._strategies: Dict[str, Type[Strategy]] = {}
        self._descriptions: Dict[str, str] = {}
    
    def register(self, 
                name: str, 
                strategy_class: Type[Strategy],
                description: str = "") -> None:
        """
        Register a strategy class.
        
        Args:
            name: Unique identifier for the strategy
            strategy_class: Strategy class (not instance)
            description: Human-readable description
        """
        if not inspect.isclass(strategy_class):
            raise ValueError(f"Expected a class, got {type(strategy_class)}")
        
        if not issubclass(strategy_class, Strategy):
            raise ValueError(f"{strategy_class} must inherit from Strategy")
        
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' is already registered")
        
        self._strategies[name] = strategy_class
        self._descriptions[name] = description or getattr(strategy_class, '__doc__', '')
    
    def unregister(self, name: str) -> None:
        """Remove a strategy from the registry."""
        if name in self._strategies:
            del self._strategies[name]
            del self._descriptions[name]
    
    def get(self, name: str) -> Optional[Type[Strategy]]:
        """Get a strategy class by name."""
        return self._strategies.get(name)
    
    def create(self, name: str, **kwargs) -> Strategy:
        """
        Create a strategy instance.
        
        Args:
            name: Registered strategy name
            **kwargs: Parameters to pass to strategy constructor
            
        Returns:
            Strategy instance
        """
        strategy_class = self.get(name)
        if strategy_class is None:
            available = self.list_strategies()
            raise ValueError(f"Strategy '{name}' not found. Available: {available}")
        
        try:
            return strategy_class(**kwargs)
        except TypeError as e:
            raise ValueError(f"Invalid parameters for {name}: {e}")
    
    def list_strategies(self) -> List[str]:
        """Get list of all registered strategy names."""
        return list(self._strategies.keys())
    
    def get_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a strategy.
        
        Returns:
            Dict with name, description, parameters, etc.
        """
        strategy_class = self.get(name)
        if strategy_class is None:
            return None
        
        # Get constructor signature to show required/optional parameters
        sig = inspect.signature(strategy_class.__init__)
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            params[param_name] = {
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty
            }
        
        return {
            'name': name,
            'class': strategy_class.__name__,
            'description': self._descriptions.get(name, ''),
            'parameters': params
        }
    
    def get_all_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered strategies."""
        return [self.get_info(name) for name in self.list_strategies()]
    
    def __repr__(self) -> str:
        return f"StrategyRegistry(strategies={len(self._strategies)})"
    
    def __len__(self) -> int:
        return len(self._strategies)


# Global registry instance
_global_registry = None


def get_global_registry() -> StrategyRegistry:
    """
    Get the global strategy registry singleton.
    
    Returns:
        StrategyRegistry instance with built-in strategies registered
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = StrategyRegistry()
        _register_builtin_strategies(_global_registry)
    return _global_registry


def _register_builtin_strategies(registry: StrategyRegistry) -> None:
    """Register all built-in strategies."""
    registry.register(
        'mfi_hunter',
        MfiHunterStrategy,
        'Momentum strategy using Money Flow Index with tiered position sizing'
    )
    
    registry.register(
        'rsi_mfi_consensus',
        RsiMfiConsensusStrategy,
        'Dual momentum confirmation using RSI and MFI - trades only when both agree'
    )
    
    # Future strategies can be registered here:
    # registry.register('macd_crossover', MACDCrossoverStrategy, 'MACD crossover strategy')
    # registry.register('bollinger_mean_reversion', BollingerMeanReversionStrategy, '')


def create_strategy(name: str, **kwargs) -> Strategy:
    """
    Convenience function to create a strategy from global registry.
    
    Example:
        strategy = create_strategy('mfi_hunter', mfi_period=16, buy_threshold=35)
    """
    registry = get_global_registry()
    return registry.create(name, **kwargs)


def list_available_strategies() -> List[str]:
    """Get list of all available strategies."""
    registry = get_global_registry()
    return registry.list_strategies()


def get_strategy_info(name: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific strategy."""
    registry = get_global_registry()
    return registry.get_info(name)
