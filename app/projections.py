from dataclasses import dataclass
from typing import Iterable, Literal, Optional

Cadence = Literal["monthly", "yearly"]


@dataclass(frozen=True)
class Account:
    name: str
    balance_pence: int
    annual_rate_bp: int = 0
    monthly_allocation_pence: int = 0
    id: Optional[int] = None


@dataclass(frozen=True)
class IncomeSource:
    name: str
    monthly_amount_pence: int
    id: Optional[int] = None


@dataclass(frozen=True)
class Expense:
    name: str
    amount_pence: int
    cadence: Cadence
    id: Optional[int] = None


def project_balance(
    principal_pence: int,
    annual_rate_bp: int,
    monthly_pence: int,
    months: int,
) -> int:
    monthly_rate = annual_rate_bp / 10_000 / 12
    if monthly_rate == 0:
        result = principal_pence + monthly_pence * months
    else:
        growth = (1 + monthly_rate) ** months
        future_principal = principal_pence * growth
        future_contributions = monthly_pence * (growth - 1) / monthly_rate
        result = round(future_principal + future_contributions)
    return result


def project_total(accounts: Iterable[Account], months: int) -> int:
    total = sum(
        project_balance(
            principal_pence=account.balance_pence,
            annual_rate_bp=account.annual_rate_bp,
            monthly_pence=account.monthly_allocation_pence,
            months=months,
        )
        for account in accounts
    )
    return total
