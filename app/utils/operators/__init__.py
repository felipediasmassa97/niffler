"""Data utils."""

from abc import ABC, abstractmethod

import pandas as pd


class Operator(ABC):
    """Data operators."""

    @property
    @abstractmethod
    def data(self) -> pd.DataFrame:
        """Data."""


# Data objects:

# Filters:

# - All transactions (incomes and expenses)
# - Incomes only
# - Expenses only

# - Date filters

# Aggregations:

# - Monthly aggregated
# - Yearly aggregated

# - Per-category aggregated
# - Per-tier aggregated (fixed, variable, lifestyle)

# Rules:

# - Actuals
# - Effectives (diluted)
