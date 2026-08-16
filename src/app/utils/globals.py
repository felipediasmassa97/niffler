"""Global variables for the app."""

from enum import StrEnum


class Account(StrEnum):
    INVESTMENTS = "Investments"
    VR = "Vale-Refeição"
    VA = "Vale-Alimentação"
    TRIP_FUNDS = "Trip Funds"
