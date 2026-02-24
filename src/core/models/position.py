"""
Position and portfolio models for tracking trades and equity.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class PositionStatus(Enum):
    """Status of a trading position."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


@dataclass
class Position:
    """
    Represents an open or closed position.
    """
    symbol: str
    entry_time: datetime
    entry_price: Decimal
    quantity: int
    status: PositionStatus = PositionStatus.OPEN
    
    # Exit information (filled when position is closed)
    exit_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    
    # Strategy context
    strategy_name: str = "Unknown"
    entry_reason: str = ""
    exit_reason: str = ""
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")
    
    @property
    def entry_value(self) -> Decimal:
        """Total value at entry."""
        return self.entry_price * Decimal(str(self.quantity))
    
    @property
    def exit_value(self) -> Optional[Decimal]:
        """Total value at exit (if closed)."""
        if self.exit_price is None:
            return None
        return self.exit_price * Decimal(str(self.quantity))
    
    @property
    def pnl(self) -> Optional[Decimal]:
        """Profit and loss (if closed)."""
        if self.exit_value is None:
            return None
        return self.exit_value - self.entry_value
    
    @property
    def pnl_percent(self) -> Optional[Decimal]:
        """Profit and loss as percentage."""
        if self.pnl is None:
            return None
        return (self.pnl / self.entry_value) * Decimal('100')
    
    @property
    def is_profitable(self) -> Optional[bool]:
        """Check if position is profitable (if closed)."""
        if self.pnl is None:
            return None
        return self.pnl > 0
    
    def close(self, exit_time: datetime, exit_price: Decimal, reason: str = "") -> None:
        """Close the position."""
        if self.status == PositionStatus.CLOSED:
            raise ValueError("Position is already closed")
        
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        self.status = PositionStatus.CLOSED
    
    def current_value(self, current_price: Decimal) -> Decimal:
        """Calculate current market value."""
        return current_price * Decimal(str(self.quantity))
    
    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L for open position."""
        return self.current_value(current_price) - self.entry_value
    
    def unrealized_pnl_percent(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L percentage."""
        return (self.unrealized_pnl(current_price) / self.entry_value) * Decimal('100')


@dataclass
class Portfolio:
    """
    Portfolio management for tracking multiple positions and overall performance.
    """
    initial_capital: Decimal
    current_cash: Decimal
    positions: dict[str, list[Position]] = field(default_factory=dict)  # symbol -> positions
    closed_positions: list[Position] = field(default_factory=list)
    
    def __post_init__(self):
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
    
    @property
    def open_positions(self) -> list[Position]:
        """Get all open positions across all symbols."""
        return [pos for positions in self.positions.values() 
                for pos in positions if pos.status == PositionStatus.OPEN]
    
    def get_position_value(self, symbol: str, current_price: Decimal) -> Decimal:
        """Calculate total position value for a symbol."""
        if symbol not in self.positions:
            return Decimal('0')
        return sum(pos.current_value(current_price) for pos in self.positions[symbol]
                  if pos.status == PositionStatus.OPEN)
    
    def get_total_equity(self, current_prices: dict[str, Decimal]) -> Decimal:
        """Calculate total equity (cash + all positions at current prices)."""
        positions_value = sum(
            self.get_position_value(symbol, current_prices.get(symbol, Decimal('0')))
            for symbol in self.positions.keys()
        )
        return self.current_cash + positions_value
    
    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio."""
        if position.symbol not in self.positions:
            self.positions[position.symbol] = []
        self.positions[position.symbol].append(position)
    
    def close_position(self, symbol: str, exit_time: datetime, 
                      exit_price: Decimal, reason: str = "") -> None:
        """Close all positions for a symbol."""
        if symbol not in self.positions:
            raise ValueError(f"No open positions for {symbol}")
        
        for pos in self.positions[symbol]:
            if pos.status == PositionStatus.OPEN:
                pos.close(exit_time, exit_price, reason)
                self.closed_positions.append(pos)
    
    @property
    def total_realized_pnl(self) -> Decimal:
        """Calculate total realized P&L from closed positions."""
        return sum(pos.pnl for pos in self.closed_positions if pos.pnl is not None)
    
    @property
    def win_rate(self) -> Optional[float]:
        """Calculate win rate from closed positions."""
        if not self.closed_positions:
            return None
        
        profitable = sum(1 for pos in self.closed_positions if pos.is_profitable)
        return profitable / len(self.closed_positions) * 100
