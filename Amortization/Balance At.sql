CREATE OR REPLACE FUNCTION public.balance_at(principal numeric, rate numeric, term integer, months_paid integer)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
/*
 * Calculates remaining loan balance after N payments
 * Use case: Loan amortization schedules, payoff quotes, portfolio valuations
 * 
 * Example: balance_at(250000, 0.065, 360, 36) 
 *          → Balance after 3 years of a 30-year mortgage at 6.5%
 */
DECLARE
  monthly_rate NUMERIC := rate / 12;
  monthly_payment NUMERIC;
  balance NUMERIC := principal;
  interest NUMERIC;
BEGIN
  -- Edge case: no payments made yet
  IF months_paid = 0 THEN
    RETURN principal;
  END IF;

  -- Edge case: loan fully paid
  IF months_paid >= term THEN
    RETURN 0;
  END IF;

  -- Calculate monthly payment using standard amortization formula
  -- PMT = P * [r(1+r)^n] / [(1+r)^n - 1]
  monthly_payment := principal * monthly_rate * POWER(1 + monthly_rate, term) 
                     / (POWER(1 + monthly_rate, term) - 1);

  -- Amortize: each payment splits into interest + principal
  FOR i IN 1..months_paid LOOP
    interest := balance * monthly_rate;
    balance := balance - (monthly_payment - interest);
  END LOOP;

  RETURN ROUND(balance, 2);
END;
$function$
;
