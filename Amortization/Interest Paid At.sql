
CREATE OR REPLACE FUNCTION public.interest_paid_at(principal numeric, rate numeric, term integer, months_paid integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  monthly_rate NUMERIC := rate / 12;
  monthly_payment NUMERIC;
  interest_total NUMERIC := 0;
  balance NUMERIC := principal;
  interest NUMERIC;
BEGIN
  monthly_payment := principal * monthly_rate / (1 - POWER(1 + monthly_rate, -term));

  FOR i IN 1..months_paid LOOP
    interest := balance * monthly_rate;
    interest_total := interest_total + interest;
    balance := balance - (monthly_payment - interest);
  END LOOP;

  RETURN ROUND(interest_total, 2);
END;
$function$
;
