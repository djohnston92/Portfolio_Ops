-- DROP FUNCTION public.interest_accrued_daily(numeric, numeric, int4);

CREATE OR REPLACE FUNCTION public.interest_accrued_daily(principal numeric, rate numeric, days integer)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$

DECLARE
    daily_rate NUMERIC := rate / 365;  -- Act/365 convention (not Act/360)
    interest_due NUMERIC;
BEGIN
    -- Validation
    IF principal <= 0 OR rate < 0 OR days < 0 THEN
        RETURN 0;
    END IF;

    interest_due := principal * daily_rate * days;
    
    RETURN ROUND(interest_due, 2);
END;

$function$
;
