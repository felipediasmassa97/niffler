"""Charts utils."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import plotly.express as px
import plotly.graph_objects as go

from utils.operators import Operator

# fixit add custom colors for categories (long-term)
# fixit make fancier charts (fine formatting on tooltip, for example) (long-term)
# use hover_data and fig.update_traces(hovertemplate=...) to customize hover tooltips
# e.g.: hovertemplate="Date: %{x|%b/%Y}<br>Value: %{y}<br>Category: %{text}"


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
            # hover_data={"Month": ":%b/%Y", "Value": ":.1f", "Type": True},
        )
        # fig.update_traces(
        #     hovertemplate="Date: %{x|%b/%Y}<br>Value: %{y}<br>Category: %{text}"
        # )
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
            # hover_data={"Month": ":%b/%Y", "Value": ":.1f"},
            barmode="group",
        )
        # fig.update_traces(
        #     hovertemplate="Date: %{x|%b/%Y}<br>Value: %{y}<br>Category: %{text}"
        # )
        return fig
