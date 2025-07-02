CREATE OR REPLACE FUNCTION public.monthly_payment(principal numeric, rate numeric, term integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  monthly_rate NUMERIC := rate / 12;
BEGIN
  RETURN ROUND(principal * monthly_rate / (1 - POWER(1 + monthly_rate, -term)), 2);
END;
$function$
;
