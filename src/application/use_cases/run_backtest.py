"""
Use Case: Run Backtest

Encapsulates the complete workflow for running a strategy backtest.
"""
from typing import Dict, Any, Optional

from ..services.backtest_service import BacktestService
from ..services.data_service import DataService
from ...core.strategies.registry import get_global_registry


class RunBacktestUseCase:
    """
    Use case for running strategy backtests.
    
    Workflow:
    1. Validate inputs
    2. Ensure data is available
    3. Create/configure strategy
    4. Run backtest
    5. Format and return results
    """
    
    def __init__(self, 
                 backtest_service: BacktestService,
                 data_service: DataService):
        self.backtest_service = backtest_service
        self.data_service = data_service
    
    def execute(self,
                symbol: str,
                strategy_name: str,
                strategy_params: Optional[Dict[str, Any]] = None,
                cash: float = 1_000_000,
                commission: float = 0.001425) -> Dict[str, Any]:
        """
        Run a backtest.
        
        Args:
            symbol: Stock symbol
            strategy_name: Name of registered strategy
            strategy_params: Strategy parameters
            cash: Initial capital
            commission: Trading commission
            
        Returns:
            Dict with backtest results
        """
        strategy_params = strategy_params or {}
        
        try:
            # Ensure data is available
            data_available = self.data_service.ensure_data_available(
                symbol, required_days=100
            )
            
            if not data_available:
                return {
                    'success': False,
                    'error': f'Insufficient data for {symbol}'
                }
            
            # Get strategy from registry
            registry = get_global_registry()
            
            # Debug: Check available strategies
            available = registry.list_strategies()
            if strategy_name not in available:
                return {
                    'success': False,
                    'error': f"Strategy '{strategy_name}' not found. Available: {available}"
                }
            
            strategy = registry.create(strategy_name, **strategy_params)
            
            # Run backtest
            results = self.backtest_service.run_backtest(
                symbol=symbol,
                strategy=strategy,
                cash=cash,
                commission=commission
            )
            
            results['success'] = True
            return results
            
        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid strategy or parameters: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Backtest failed: {str(e)}'
            }
    
    def execute_optimization(self,
                           symbol: str,
                           strategy_name: str,
                           param_ranges: Dict[str, range],
                           maximize: str = 'Return [%]',
                           cash: float = 1_000_000,
                           commission: float = 0.001425) -> Dict[str, Any]:
        """
        Run parameter optimization.
        
        Args:
            symbol: Stock symbol
            strategy_name: Name of registered strategy
            param_ranges: Parameter ranges to optimize
            maximize: Metric to optimize
            cash: Initial capital
            commission: Trading commission
            
        Returns:
            Dict with optimization results
        """
        try:
            # Ensure data is available
            data_available = self.data_service.ensure_data_available(
                symbol, required_days=100
            )
            
            if not data_available:
                return {
                    'success': False,
                    'error': f'Insufficient data for {symbol}'
                }
            
            # Get strategy from registry
            registry = get_global_registry()
            strategy = registry.create(strategy_name)
            
            # Run optimization
            results = self.backtest_service.optimize(
                symbol=symbol,
                strategy=strategy,
                param_ranges=param_ranges,
                maximize=maximize,
                cash=cash,
                commission=commission
            )
            
            results['success'] = True
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Optimization failed: {str(e)}'
            }
