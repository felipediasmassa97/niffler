"""Charts utils."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import plotly.express as px
import plotly.graph_objects as go

from utils.operators import Operator

# fixit long-term add custom colors for categories


@dataclass
class BarChart(ABC):
    """Bar chart."""

    operator: Operator
    column_x: str
    column_y: str
    column_cat: str = None
    column_text: str = None
    column_cat_orders: dict[str, list[str]] = None
    title: str = None

    @property
    @abstractmethod
    def chart(self) -> go.Figure:
        """Chart figure."""

    @property
    @abstractmethod
    def hover_template(self) -> str:
        """Hover template."""


class SimpleBarChart(BarChart):
    """Simple bar chart."""

    @property
    def chart(self) -> go.Figure:
        fig = px.bar(
            self.operator.data,
            x=self.column_x,
            y=self.column_y,
            color=self.column_cat,
            text=self.column_text,
            category_orders=self.column_cat_orders,
            title=self.title,
        )
        fig.update_traces(hovertemplate=self.hover_template)
        return fig


class GroupedBarChart(BarChart):
    """Grouped bar chart."""

    @property
    def chart(self) -> go.Figure:
        fig = px.bar(
            self.operator.data,
            x=self.column_x,
            y=self.column_y,
            color=self.column_cat,
            text=self.column_text,
            category_orders=self.column_cat_orders,
            title=self.title,
            barmode="group",
        )
        fig.update_traces(hovertemplate=self.hover_template)
        return fig


class MonthlyTrendSimpleBarChart(SimpleBarChart):
    """Monthly trend simple bar chart."""

    @property
    def hover_template(self) -> str:
        """Hover template."""
        return (
            "<b>%{fullData.name}</b><br>"
            "Month: %{x|%b/%y}<br>"
            "Value: R$ %{y:,.2f}"
            "<extra></extra>"
        )


class MonthlyTrendGroupedBarChart(GroupedBarChart):
    """Monthly trend grouped bar chart."""

    @property
    def hover_template(self) -> str:
        """Hover template."""
        return (
            "<b>%{fullData.name}</b><br>"
            "Month: %{x|%b/%y}<br>"
            "Value: R$ %{y:,.2f}"
            "<extra></extra>"
        )


class PeriodSummarySimpleBarChart(SimpleBarChart):
    """Period summary simple bar chart."""

    @property
    def hover_template(self) -> str:
        """Hover template."""
        return "<b>%{x}</b><br>Value: R$ %{y:,.2f}<extra></extra>"
