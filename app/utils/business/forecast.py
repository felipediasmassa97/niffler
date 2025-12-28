"""Expense forecast rules."""

# If a category must be projected, its actual costs are projected to the full period proportionally to date
# If a category must not be projected, its actual costs are taken as-is without projection
CATEGORY_MUST_PROJECT = {
    "car": True,  # because most transactions are distributed (gas)
    "health": True,  # because most transactions are weekly (therapy)
    "home": True,  # because it is actionable
    "personal felp": True,  # because it is actionable
    "personal lena": True,  # because it is actionable
    "recreation": True,  # because it is actionable
    "restaurant": True,  # because it is actionable
    "transport": True,  # because most transactions are distributed (Uber)
    "unknown": True,  # because no good reason not to be
    "work lunch": True,  # because it is actionable
    "commute": False,  # because transactions are lumped sums (card recharge)
    "donation": False,  # because of irregularity
    "education": False,  # because transactions are one-shot (graduation)
    "gift": False,  # because of irregularity
    "high costs": False,  # because of irregularity
    "maintenance": False,  # because of irregularity
    "pharmacy": True,  # because of irregularity
    "physical": False,  # because transactions are one-shot or irregular
    "rent": False,  # because transactions are one-shot
    "services": False,  # because transactions are monthly
    "subscriptions": False,  # because transactions are one-shot
    "supermarket": False,  # because most expensive transaction is monthly
    "travel": False,  # because of irregularity
    "work": False,  # because of irregularity
}
