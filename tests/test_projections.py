from app.projections import project_balance


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
