CREATE OR REPLACE FUNCTION public.balance_at(principal numeric, rate numeric, term integer, months_paid integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  monthly_rate NUMERIC := rate / 12;
  monthly_payment NUMERIC;
  balance NUMERIC := principal;
  interest NUMERIC;
BEGIN
  -- Calculate monthly payment using amortization formula
  monthly_payment := principal * monthly_rate / (1 - POWER(1 + monthly_rate, -term));

  -- Simulate monthly payments up to months_paid
  FOR i IN 1..months_paid LOOP
    interest := balance * monthly_rate;
    balance := balance - (monthly_payment - interest);
  END LOOP;

  RETURN ROUND(balance, 2);
END;
$function$
;
