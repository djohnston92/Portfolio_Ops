CREATE OR REPLACE FUNCTION public.chi_square_test(row_cat text[], col_cat text[], n numeric[], alpha numeric DEFAULT 0.05)
 RETURNS TABLE(n_rows integer, n_cols integer, total_n numeric, chi_square numeric, df integer, critical_value numeric, p_value double precision, cramers_v numeric, min_expected numeric, cells_expected_under_5 integer, significant boolean, conclusion text)
 LANGUAGE plpgsql
 STABLE
AS $function$
declare
    k_r integer; k_c integer; tot numeric; x double precision; mine numeric; under5 integer;
    d integer; p double precision; crit double precision;
begin
    -- same math as chi_square_cells, kept unrounded here
    with cells as (
        select coalesce(r, '(null)') r, coalesce(c, '(null)') c, sum(coalesce(v, 0)) o
        from unnest(row_cat, col_cat, n) u(r, c, v) group by 1, 2
    ), rs as (select r, sum(o) rt from cells group by r),
       cs as (select c, sum(o) ct from cells group by c),
       t as (select sum(o) t from cells),
    grid as (
        select coalesce(cells.o, 0) o, rs.rt * cs.ct / t.t e
        from rs cross join cs cross join t
        left join cells on cells.r = rs.r and cells.c = cs.c
    )
    select (select count(*) from rs), (select count(*) from cs), (select t.t from t),
           sum(case when e > 0 then ((o - e) ^ 2 / e)::double precision end), min(e), count(*) filter (where e < 5)
      into k_r, k_c, tot, x, mine, under5
      from grid;

    if k_r < 2 or k_c < 2 then
        raise exception 'Need at least 2 row categories and 2 column categories, got % x %', k_r, k_c;
    end if;

    d := (k_r - 1) * (k_c - 1);
    p := claude_workspace.chi_square_sf(x, d);
    crit := claude_workspace.chi_square_critical(alpha::double precision, d);

    if under5 > 0 then
        raise notice '% cell(s) have an expected count under 5; the chi-square approximation is shaky there.', under5;
    end if;

    return query select k_r, k_c, tot, round(x::numeric, 4), d, round(crit::numeric, 4), p,
        round(sqrt(x / (tot * (least(k_r, k_c) - 1)))::numeric, 4),
        round(mine, 2), under5, p < alpha,
        case when p < alpha
             then 'Reject the null hypothesis: the row and column categories are not independent.'
             else 'Fail to reject the null hypothesis: no significant association between the categories.' end;
end $function$
;
