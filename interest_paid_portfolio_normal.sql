-- DROP FUNCTION public.interest_paid_portfolio_normal(numeric, numeric, int4, int4);

CREATE OR REPLACE FUNCTION public.interest_paid_portfolio_normal(principal numeric, prime_rate numeric, term integer, months_paid integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Credit tier weights
    wt_super NUMERIC := 0.10;
    wt_prime NUMERIC := 0.30;
    wt_near  NUMERIC := 0.20;
    wt_sub   NUMERIC := 0.25;
    wt_deep  NUMERIC := 0.15;

    -- APRs based on prime rate
    rate_super NUMERIC := prime_rate + 0.01;
    rate_prime NUMERIC := prime_rate + 0.03;
    rate_near  NUMERIC := prime_rate + 0.055;
    rate_sub   NUMERIC := prime_rate + 0.125;
    rate_deep  NUMERIC := prime_rate + 0.175;

    -- Tracking interest per tier
    total_interest NUMERIC := 0;

    -- Utility vars
    seg_principal NUMERIC;
    seg_rate NUMERIC;
    seg_weight NUMERIC;
    seg_interest NUMERIC;
    seg_monthly NUMERIC;
    seg_balance NUMERIC;
    seg_interest_month NUMERIC;
BEGIN
    -- Iterate over tiers
    FOR seg_weight, seg_rate IN
        SELECT * FROM (
            VALUES
                (wt_super, rate_super),
                (wt_prime, rate_prime),
                (wt_near,  rate_near),
                (wt_sub,   rate_sub),
                (wt_deep,  rate_deep)
        ) AS t(weight, rate)
    LOOP
        seg_principal := principal * seg_weight;
        seg_balance := seg_principal;
        seg_monthly := seg_principal * (seg_rate / 12) / (1 - POWER(1 + seg_rate / 12, -term));
        seg_interest := 0;

        FOR i IN 1..months_paid LOOP
            seg_interest_month := seg_balance * (seg_rate / 12);
            seg_interest := seg_interest + seg_interest_month;
            seg_balance := seg_balance - (seg_monthly - seg_interest_month);
        END LOOP;

        total_interest := total_interest + seg_interest;
    END LOOP;

    RETURN ROUND(total_interest, 2);
END;
$function$
;
