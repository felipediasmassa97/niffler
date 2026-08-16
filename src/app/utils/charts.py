"""Charts utils."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import plotly.express as px
import plotly.graph_objects as go

from utils.data import Operator


@dataclass
class BarChart(ABC):
    """Bar chart."""

    operator: Operator
    column_x: str
    column_y: str
    column_cat: str = None
    column_text: str = None
    title: str = None

    @property
    @abstractmethod
    def chart(self) -> go.Figure:
        """Chart figure."""


class SimpleBarChart(BarChart):
    """Simple bar chart."""

    @property
    def chart(self) -> go.Figure:
        return px.bar(
            self.operator.data,
            x=self.column_x,
            y=self.column_y,
            color=self.column_cat,
            text=self.column_text,
            title=self.title,
        )


class GroupedBarChart(BarChart):
    """Grouped bar chart."""

    @property
    def chart(self) -> go.Figure:
        return px.bar(
            self.operator.data,
            x=self.column_x,
            y=self.column_y,
            color=self.column_cat,
            text=self.column_text,
            title=self.title,
            barmode="group",
        )
