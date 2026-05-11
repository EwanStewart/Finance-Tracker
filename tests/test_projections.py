from app.projections import Account, project_balance, project_total


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
