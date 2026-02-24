"""
Core strategies module.

Exports all strategy classes for easy importing.
"""
from .base import (
    Strategy,
    MomentumStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    CompositeStrategy
)
from .mfi_hunter import MfiHunterStrategy
from .rsi_mfi_consensus import RsiMfiConsensusStrategy
from .registry import (
    StrategyRegistry,
    get_global_registry,
    create_strategy,
    list_available_strategies,
    get_strategy_info
)

__all__ = [
    'Strategy',
    'MomentumStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'CompositeStrategy',
    'MfiHunterStrategy',
    'RsiMfiConsensusStrategy',
    'StrategyRegistry',
    'get_global_registry',
    'create_strategy',
    'list_available_strategies',
    'get_strategy_info',
]
