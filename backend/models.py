"""
Pydantic models for dashboard data structures
Matches TypeScript interfaces for type safety and validation
"""

from typing import List, Literal, Optional, Union
from pydantic import BaseModel


class MetricData(BaseModel):
    """Metric data model matching TypeScript MetricData interface"""
    id: str
    title: str
    value: Union[int, str]  # Can be number or string (e.g., "$45,231" or "3.2%")
    change: Optional[float] = None
    trend: Optional[Literal["up", "down", "neutral"]] = None


class ChartDataPoint(BaseModel):
    """Chart data point model - flexible to support different chart types"""
    date: Optional[str] = None  # For line charts
    category: Optional[str] = None  # For bar charts
    name: Optional[str] = None  # For pie charts
    value: float
    label: Optional[str] = None
    color: Optional[str] = None  # Optional color for pie chart segments


class ChartData(BaseModel):
    """Chart data model matching TypeScript ChartData interface"""
    id: str
    type: Literal["line", "bar", "pie"]
    title: str
    data: List[ChartDataPoint]
    color: Optional[str] = None


class DashboardData(BaseModel):
    """Complete dashboard data model matching TypeScript DashboardData interface"""
    metrics: List[MetricData]
    charts: List[ChartData]
