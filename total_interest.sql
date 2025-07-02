CREATE OR REPLACE FUNCTION public.total_interest(principal numeric, rate numeric, term integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  monthly_rate NUMERIC := rate / 12;
  monthly_payment NUMERIC;
BEGIN
  monthly_payment := principal * monthly_rate / (1 - POWER(1 + monthly_rate, -term));
  RETURN ROUND((monthly_payment * term) - principal, 2);
END;
$function$
;
