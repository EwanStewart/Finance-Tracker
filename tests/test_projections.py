from app.projections import (
    Account,
    Expense,
    IncomeSource,
    monthly_interest,
    monthly_summary,
    project_balance,
    project_total,
    total_monthly_interest,
    unallocated_surplus,
)


def test_project_balance_with_zero_rate_is_linear():
    result = project_balance(
        principal_pence=100_00,
        annual_rate_bp=0,
        monthly_pence=100_00,
        months=12,
    )

    assert result == 100_00 + 12 * 100_00


def test_project_balance_compounds_principal_at_monthly_rate():
    result = project_balance(
        principal_pence=1_000_00,
        annual_rate_bp=1200,
        monthly_pence=0,
        months=12,
    )

    assert result == 112_683


def test_project_balance_adds_compounded_monthly_contributions():
    result = project_balance(
        principal_pence=1_000_00,
        annual_rate_bp=1200,
        monthly_pence=100_00,
        months=12,
    )

    assert result == 239_508


def test_project_total_returns_zero_for_no_accounts():
    result = project_total([], months=12)

    assert result == 0


def test_project_total_sums_projected_balances_across_accounts():
    accounts = [
        Account(
            name="A", balance_pence=100_00, annual_rate_bp=0, monthly_allocation_pence=0
        ),
        Account(
            name="B",
            balance_pence=200_00,
            annual_rate_bp=0,
            monthly_allocation_pence=10_00,
        ),
    ]

    result = project_total(accounts, months=12)

    assert result == 100_00 + 200_00 + 12 * 10_00


def test_project_total_handles_negative_balances():
    accounts = [
        Account(
            name="Savings",
            balance_pence=500_00,
            annual_rate_bp=0,
            monthly_allocation_pence=0,
        ),
        Account(
            name="Credit Card",
            balance_pence=-100_00,
            annual_rate_bp=0,
            monthly_allocation_pence=0,
        ),
    ]

    result = project_total(accounts, months=12)

    assert result == 400_00


def test_project_total_accumulates_unallocated_surplus_as_cash():
    accounts = [
        Account(
            name="A", balance_pence=100_00, annual_rate_bp=0, monthly_allocation_pence=0
        )
    ]

    result = project_total(accounts, months=12, surplus_pence=50_00)

    assert result == 100_00 + 12 * 50_00


def test_unallocated_surplus_is_what_is_left_after_allocations():
    accounts = [
        Account(name="A", balance_pence=0, monthly_allocation_pence=300_00),
        Account(name="B", balance_pence=0, monthly_allocation_pence=200_00),
    ]

    result = unallocated_surplus(accounts, available_to_save_pence=800_00)

    assert result == 300_00


def test_unallocated_surplus_never_goes_negative_when_over_allocated():
    accounts = [Account(name="A", balance_pence=0, monthly_allocation_pence=900_00)]

    result = unallocated_surplus(accounts, available_to_save_pence=800_00)

    assert result == 0


def test_monthly_summary_is_zero_when_no_data():
    result = monthly_summary([], [])

    assert result == {
        "income_pence": 0,
        "monthly_expense_pence": 0,
        "yearly_expense_pence": 0,
        "yearly_monthly_equivalent_pence": 0,
        "available_to_save_pence": 0,
    }


def test_monthly_summary_subtracts_monthly_and_yearly_expenses():
    income = [IncomeSource(name="Salary", monthly_amount_pence=2_954_00)]
    expenses = [
        Expense(name="Rent", amount_pence=200_00, cadence="monthly"),
        Expense(name="Phone", amount_pence=10_90, cadence="monthly"),
        Expense(name="Car Insurance", amount_pence=700_00, cadence="yearly"),
        Expense(name="Road Tax", amount_pence=200_00, cadence="yearly"),
    ]

    result = monthly_summary(income, expenses)

    assert result["income_pence"] == 2_954_00
    assert result["monthly_expense_pence"] == 210_90
    assert result["yearly_expense_pence"] == 900_00
    assert result["yearly_monthly_equivalent_pence"] == round(900_00 / 12)
    assert result["available_to_save_pence"] == 2_954_00 - 210_90 - round(900_00 / 12)


def test_monthly_interest_divides_the_annual_rate_over_twelve_months():
    account = Account(name="Cash ISA", balance_pence=10_000_00, annual_rate_bp=345)

    assert monthly_interest(account) == 2_875


def test_monthly_interest_is_zero_without_a_rate():
    account = Account(name="Current", balance_pence=5_000_00, annual_rate_bp=0)

    assert monthly_interest(account) == 0


def test_monthly_interest_on_a_card_balance_is_a_charge():
    card = Account(
        name="Credit card",
        balance_pence=-1_200_00,
        annual_rate_bp=2400,
        kind="credit_card",
    )

    assert monthly_interest(card) == -2_400


def test_total_monthly_interest_adds_every_account():
    accounts = [
        Account(name="Cash ISA", balance_pence=10_000_00, annual_rate_bp=345),
        Account(name="Reward saver", balance_pence=2_000_00, annual_rate_bp=600),
    ]

    assert total_monthly_interest(accounts) == 2_875 + 1_000


def test_an_investment_account_accrues_no_interest():
    account = Account(
        name="S&S ISA",
        balance_pence=17_615_25,
        annual_rate_bp=1110,
        accrues_interest=False,
    )

    assert monthly_interest(account) == 0
