"""Charts utils."""

import plotly.express as px
import plotly.graph_objects as go

from utils.data import Operator


class BarChart:
    """Bar chart."""

    def __init__(
        self,
        operator: Operator,
        column_x: str,
        column_y: str,
        column_cat: str,
        title: str,
    ) -> go.Figure:
        self.chart = px.bar(
            operator.data,
            x=column_x,
            y=column_y,
            color=column_cat,
            text=column_cat,
            title=title,
        )
