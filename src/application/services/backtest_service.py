"""
Backtesting Service - Application layer for strategy backtesting.

Orchestrates backtesting operations using the backtesting library
and our strategy framework.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy as BacktestStrategy
try:
    import pandas_ta as ta
except ImportError:
    ta = None

from ...core.strategies.base import Strategy as CoreStrategy
from ...core.models.signal import SignalType
from .data_service import DataService


class BacktestService:
    """
    Service for running strategy backtests.
    
    This bridges our strategy framework with the backtesting library,
    providing a clean interface for testing strategies.
    """
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service
    
    @staticmethod
    def _ensure_timezone_naive(df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggressively remove timezone info from DataFrame.
        
        backtesting.py library REQUIRES timezone-naive datetimes.
        This helper ensures all datetimes are stripped of timezone info.
        """
        df = df.copy()
        
        # Strip timezone from index
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        # Strip timezone from any datetime columns
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                if hasattr(df[col], 'dt') and hasattr(df[col].dt, 'tz') and df[col].dt.tz is not None:
                    df[col] = df[col].dt.tz_localize(None)
        
        return df
    
    def create_backtest_strategy(self, core_strategy: CoreStrategy) -> type:
        """
        Create a backtesting.Strategy class from our CoreStrategy.
        
        This adapter allows our strategies to work with the backtesting library.
        
        Args:
            core_strategy: Our strategy instance
            
        Returns:
            A class compatible with backtesting library
        """
        class StrategyAdapter(BacktestStrategy):
            """Adapter to make our strategy work with backtesting library."""
            
            def init(self):
                """Initialize strategy - called once before backtesting starts."""
                # Convert self.data to DataFrame for core strategy
                # self.data is backtesting._Data object, need to convert
                try:
                    # CRITICAL: backtesting._Data.index might be object dtype, not DatetimeIndex!
                    # Convert backtesting's _Data object to a DataFrame
                    # Data should already be timezone-naive from DataProvider
                    df = pd.DataFrame({
                        'Open': self.data.Open,
                        'High': self.data.High,
                        'Low': self.data.Low,
                        'Close': self.data.Close,
                        'Volume': self.data.Volume
                    }, index=self.data.index)
                    
                    # Initialize our core strategy with DataFrame
                    core_strategy.initialize(df)
                    
                    # Store reference to our strategy
                    self._core_strategy = core_strategy
                except Exception as e:
                    print(f"Error in strategy init: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            
            def next(self):
                """Called on each bar during backtesting."""
                try:
                    # Convert self.data to DataFrame for signal generation
                    # Data should already be timezone-naive from DataProvider
                    df = pd.DataFrame({
                        'Open': self.data.Open,
                        'High': self.data.High,
                        'Low': self.data.Low,
                        'Close': self.data.Close,
                        'Volume': self.data.Volume
                    }, index=self.data.index)
                    
                    # Copy over any calculated indicators
                    if hasattr(core_strategy, '_state') and 'mfi_values' in core_strategy._state:
                        df['MFI'] = core_strategy._state['mfi_values']
                    
                    # Generate signal using our strategy
                    signal = core_strategy.generate_signal(df, index=-1)
                except Exception as e:
                    print(f"Error in strategy next: {e}")
                    import traceback
                    traceback.print_exc()
                    return
                
                if signal is None:
                    return
                
                # Execute based on signal type
                if signal.is_entry_signal:
                    # Calculate position size
                    position_size = float(signal.recommended_position_size or 0.15)
                    
                    # Buy signal
                    if not self.position:
                        self.buy(size=position_size)
                    elif self.position.size / self.equity < 0.8:
                        # Add to position if under max
                        self.buy(size=position_size)
                
                elif signal.is_exit_signal:
                    # Sell signal - close position
                    if self.position:
                        self.position.close()
        
        return StrategyAdapter
    
    def run_backtest(self,
                    symbol: str,
                    strategy: CoreStrategy,
                    cash: float = 1_000_000,
                    commission: float = 0.001425,
                    **backtest_kwargs) -> Dict[str, Any]:
        """
        Run a backtest for a strategy on a symbol.
        
        Args:
            symbol: Stock symbol to test
            strategy: Strategy instance
            cash: Initial capital
            commission: Trading commission (default: 0.1425% for Taiwan)
            **backtest_kwargs: Additional parameters for Backtest
            
        Returns:
            Dict with backtest results and statistics
        """
        # Get data
        df = self.data_service.get_data(symbol)
        
        if df.empty:
            raise ValueError(f"No data available for {symbol}")
        
        # Ensure required columns exist and are properly formatted
        # Create a clean copy with only OHLCV columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Check which columns are available
        available_cols = [col for col in required_cols if col in df.columns]
        
        if len(available_cols) != len(required_cols):
            raise ValueError(f"Missing required columns. Available: {df.columns.tolist()}")
        
        # Create clean DataFrame with proper column names
        clean_df = pd.DataFrame({
            'Open': df['Open'].values,
            'High': df['High'].values,
            'Low': df['Low'].values,
            'Close': df['Close'].values,
            'Volume': df['Volume'].values,
        }, index=df.index)
        
        df = clean_df
        
        # Verify the data is clean (should be guaranteed by DataProvider)
        assert isinstance(df.index, pd.DatetimeIndex), f"Expected DatetimeIndex, got {type(df.index)}"
        assert df.index.tz is None, f"Data provider returned timezone-aware data: {df.index.tz}"
        
        # Create backtest strategy class
        BacktestStrategyClass = self.create_backtest_strategy(strategy)
        
        # Set up backtest
        bt = Backtest(
            df,
            BacktestStrategyClass,
            cash=cash,
            commission=commission,
            trade_on_close=True,
            **backtest_kwargs
        )
        
        # Run backtest
        stats = bt.run()
        
        # Convert stats to dict for easier handling
        results = {
            'symbol': symbol,
            'strategy': strategy.name,
            'start_date': df.index[0],
            'end_date': df.index[-1],
            'duration_days': (df.index[-1] - df.index[0]).days,
            
            # Performance metrics
            'return_pct': stats['Return [%]'],
            'buy_hold_return_pct': stats['Buy & Hold Return [%]'],
            'num_trades': stats['# Trades'],
            'win_rate_pct': stats['Win Rate [%]'],
            'best_trade_pct': stats['Best Trade [%]'],
            'worst_trade_pct': stats['Worst Trade [%]'],
            'avg_trade_pct': stats['Avg. Trade [%]'],
            
            # Risk metrics
            'max_drawdown_pct': stats['Max. Drawdown [%]'],
            'avg_drawdown_pct': stats['Avg. Drawdown [%]'],
            'sharpe_ratio': stats['Sharpe Ratio'],
            'sortino_ratio': stats['Sortino Ratio'],
            'calmar_ratio': stats['Calmar Ratio'],
            
            # Equity / Capital
            'equity_final': stats.get('Equity Final [$]', 0),
            'equity_peak': stats.get('Equity Peak [$]', 0),
            
            # Exposure
            'exposure_time_pct': stats['Exposure Time [%]'],
            
            # Full stats object for plotting
            '_full_stats': stats,
            '_backtest': bt
        }
        
        return results
    
    def optimize(self,
                symbol: str,
                strategy: CoreStrategy,
                param_ranges: Dict[str, range],
                maximize: str = 'Return [%]',
                constraint: Optional[callable] = None,
                cash: float = 1_000_000,
                commission: float = 0.001425,
                max_tries: Optional[int] = None) -> Dict[str, Any]:
        """
        Optimize strategy parameters.
        
        Args:
            symbol: Stock symbol
            strategy: Strategy instance
            param_ranges: Dict mapping parameter names to ranges
            maximize: Metric to optimize (default: 'Return [%]')
            constraint: Optional constraint function
            cash: Initial capital
            commission: Trading commission
            max_tries: Maximum optimization iterations
            
        Returns:
            Dict with best parameters and performance
        """
        # Get data
        df = self.data_service.get_data(symbol)
        
        if df.empty:
            raise ValueError(f"No data available for {symbol}")
        
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # Create dynamic strategy class with parameters
        class OptimizableStrategy(BacktestStrategy):
            """Strategy class that accepts optimization parameters."""
            
            # Define parameters from param_ranges
            for param_name, param_range in param_ranges.items():
                locals()[param_name] = param_range.start
            
            def init(self):
                # Update core strategy parameters
                for param_name in param_ranges.keys():
                    setattr(strategy, param_name, getattr(self, param_name))
                
                # Initialize strategy
                strategy.initialize(self.data)
            
            def next(self):
                signal = strategy.generate_signal(self.data, index=-1)
                
                if signal is None:
                    return
                
                if signal.is_entry_signal:
                    position_size = float(signal.recommended_position_size or 0.15)
                    if not self.position or self.position.size / self.equity < 0.8:
                        self.buy(size=position_size)
                
                elif signal.is_exit_signal:
                    if self.position:
                        self.position.close()
        
        # Set up backtest
        bt = Backtest(
            df,
            OptimizableStrategy,
            cash=cash,
            commission=commission,
            trade_on_close=True
        )
        
        # Run optimization
        stats = bt.optimize(
            **param_ranges,
            maximize=maximize,
            constraint=constraint,
            max_tries=max_tries,
            return_heatmap=False
        )
        
        # Extract optimized parameters
        optimized_params = {}
        for param_name in param_ranges.keys():
            optimized_params[param_name] = stats._strategy.__dict__.get(param_name)
        
        return {
            'symbol': symbol,
            'strategy': strategy.name,
            'optimized_params': optimized_params,
            'return_pct': stats['Return [%]'],
            'win_rate_pct': stats['Win Rate [%]'],
            'num_trades': stats['# Trades'],
            'sharpe_ratio': stats['Sharpe Ratio'],
            'max_drawdown_pct': stats['Max. Drawdown [%]'],
            '_full_stats': stats
        }
    
    def compare_strategies(self,
                          symbol: str,
                          strategies: list[CoreStrategy],
                          cash: float = 1_000_000,
                          commission: float = 0.001425) -> pd.DataFrame:
        """
        Compare multiple strategies on the same symbol.
        
        Args:
            symbol: Stock symbol
            strategies: List of strategy instances
            cash: Initial capital
            commission: Trading commission
            
        Returns:
            DataFrame with comparison results
        """
        results = []
        
        for strategy in strategies:
            try:
                result = self.run_backtest(
                    symbol, strategy, cash, commission
                )
                results.append(result)
            except Exception as e:
                print(f"Failed to backtest {strategy.name}: {e}")
        
        if not results:
            return pd.DataFrame()
        
        # Create comparison dataframe
        df = pd.DataFrame(results)
        
        # Select key metrics for comparison
        comparison_cols = [
            'strategy', 'return_pct', 'win_rate_pct', 'num_trades',
            'sharpe_ratio', 'max_drawdown_pct', 'exposure_time_pct'
        ]
        
        available_cols = [col for col in comparison_cols if col in df.columns]
        df = df[available_cols]
        
        # Sort by return
        df = df.sort_values('return_pct', ascending=False)
        
        return df
    
    def plot_results(self, results: Dict[str, Any], filename: Optional[str] = None):
        """
        Plot backtest results.
        
        Args:
            results: Results dict from run_backtest()
            filename: Optional filename to save plot
        """
        bt = results.get('_backtest')
        if bt:
            bt.plot(filename=filename, open_browser=False)
