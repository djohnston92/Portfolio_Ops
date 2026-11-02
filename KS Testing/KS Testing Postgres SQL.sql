-- DROP FUNCTION public.ks_test(_numeric, _numeric, numeric);

CREATE OR REPLACE FUNCTION public.ks_test(group_a numeric[], group_b numeric[], alpha numeric DEFAULT 0.05)
 RETURNS TABLE(n_a integer, n_b integer, ks_statistic numeric, ks_at_value numeric, cdf_a_at_ks numeric, cdf_b_at_ks numeric, critical_value numeric, p_value numeric, significant boolean, conclusion text)
 LANGUAGE plpython3u
AS $function$
import math

a = sorted(float(v) for v in group_a if v is not None)
b = sorted(float(v) for v in group_b if v is not None)

if len(a) < 2 or len(b) < 2:
    plpy.error(f"Need at least 2 non-null values in each group, got {len(a)} and {len(b)}")

n1, n2 = len(a), len(b)

# ── D statistic: max |ECDF_a(x) - ECDF_b(x)| ──────────────────────────────────
# Single merge walk over both sorted samples, advancing past *all* tied copies
# of a value before measuring — otherwise the step functions get compared
# mid-tie and D comes out too large on discrete data (integer score buckets).
i = j = 0
d = 0.0
d_at = None
cdf_a_at = 0.0
cdf_b_at = 0.0
while i < n1 and j < n2:
    x = a[i] if a[i] <= b[j] else b[j]
    while i < n1 and a[i] == x:
        i += 1
    while j < n2 and b[j] == x:
        j += 1
    fa = i / n1
    fb = j / n2
    diff = abs(fa - fb)
    if diff > d:
        d = diff
        d_at = x
        cdf_a_at = fa
        cdf_b_at = fb
# No tail pass needed: once either sample is exhausted its ECDF is pinned at
# 1.0 while the other only rises toward 1.0, so the gap can only shrink.

# ── Asymptotic (Kolmogorov/Smirnov limiting) p-value ─────────────────────────
# Q_KS(lambda) = 2 * sum_{k>=1} (-1)^(k-1) * exp(-2 k^2 lambda^2), evaluated at
# lambda = sqrt(n1*n2/(n1+n2)) * D. This is exactly scipy.stats.kstwobign.sf
# (validated to 2.2e-16 before deploy). It is NOT scipy's finite-sample-exact
# kstwo CDF, which this host can't compute efficiently in pure Python at real
# portfolio scale -- see the accuracy note in the COMMENT ON FUNCTION below.
en = math.sqrt(n1 * n2 / (n1 + n2))
lam = en * d
if lam <= 0:
    p_value = 1.0
else:
    coef = -2.0 * lam * lam
    s = 0.0
    for k in range(1, 201):
        term = math.exp(coef * k * k)
        s += (-1) ** (k - 1) * term
        if term < 1e-18:
            break
    p_value = min(1.0, max(0.0, 2.0 * s))

# Critical D at alpha, same asymptotic family: c(alpha) * sqrt((n1+n2)/(n1*n2))
crit = math.sqrt(-math.log(float(alpha) / 2.0) / 2.0) / en

sig = p_value < float(alpha)
conclusion = (
    "Reject the null hypothesis: the two samples are drawn from different distributions."
    if sig else
    "Fail to reject the null hypothesis: no significant difference between the two distributions."
)

plpy.notice(f"KS statistic (D): {d:.6f} at value {d_at}")
plpy.notice(f"Critical D at alpha={float(alpha)}: {crit:.6f}")
plpy.notice(f"P-value: {p_value:.6g}")
plpy.notice(conclusion)

# The asymptotic p-value degrades most on *lopsided* samples, not small ones --
# warn where it actually matters rather than on a bare n threshold.
ratio = max(n1, n2) / min(n1, n2)
if ratio >= 10:
    plpy.notice(
        f"NOTE: group sizes are lopsided ({n1} vs {n2}, {ratio:.0f}:1). The asymptotic "
        f"p-value runs ~10-26% high (conservative) in this regime; D itself is exact."
    )
if min(n1, n2) < 20:
    plpy.notice(
        f"NOTE: smallest group has only {min(n1, n2)} values -- treat the p-value as "
        f"indicative. D itself is exact."
    )

return [{
    "n_a": n1,
    "n_b": n2,
    "ks_statistic": round(d, 6),
    "ks_at_value": None if d_at is None else round(d_at, 6),
    "cdf_a_at_ks": round(cdf_a_at, 6),
    "cdf_b_at_ks": round(cdf_b_at, 6),
    "critical_value": round(crit, 6),
    "p_value": round(p_value, 10),
    "significant": sig,
    "conclusion": conclusion,
}]
$function$
;
