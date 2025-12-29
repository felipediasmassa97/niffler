"""Expense forecast rules."""

# If a category must be projected, its actual costs are projected to the full period proportionally to date
# If a category must not be projected, its actual costs are taken as-is without projection
CATEGORY_MUST_PROJECT = {
    "Car": True,  # because most transactions are distributed (gas)
    "Health": True,  # because most transactions are weekly (therapy)
    "Home": True,  # because it is actionable
    "Personal Felp": True,  # because it is actionable
    "Personal Lena": True,  # because it is actionable
    "Recreation": True,  # because it is actionable
    "Restaurant": True,  # because it is actionable
    "Transport": True,  # because most transactions are distributed (Uber)
    "Unknown": True,  # because no good reason not to be
    "Work Lunch": True,  # because it is actionable
    "Commute": False,  # because transactions are lumped sums (card recharge)
    "Donation": False,  # because of irregularity
    "Education": False,  # because transactions are one-shot (graduation)
    "Gift": False,  # because of irregularity
    "High Costs": False,  # because of irregularity
    "Maintenance": False,  # because of irregularity
    "Pharmacy": True,  # because of irregularity
    "Physical": False,  # because transactions are one-shot or irregular
    "Rent": False,  # because transactions are one-shot
    "Services": False,  # because transactions are monthly
    "Subscriptions": False,  # because transactions are one-shot
    "Supermarket": False,  # because most expensive transaction is monthly
    "Travel": False,  # because of irregularity
    "Work": False,  # because of irregularity
}
