

CREATE OR REPLACE FUNCTION public.chi_square_critical(alpha double precision, df integer)
 RETURNS double precision
 LANGUAGE plpgsql
 IMMUTABLE STRICT
AS $function$
declare lo double precision := 0; hi double precision := df + 10 * sqrt(2.0 * df) + 50; mid double precision;
begin
    while public.chi_square_sf(hi, df) > alpha loop hi := hi * 2; end loop;
    for i in 1..200 loop
        mid := (lo + hi) / 2;
        if public.chi_square_sf(mid, df) > alpha then lo := mid; else hi := mid; end if;
        exit when hi - lo < 1e-10;
    end loop;
    return (lo + hi) / 2;
end $function$
;
