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
