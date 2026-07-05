import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import duckdb
import numpy as np
import pandas as pd
import duckdb 
from sqlalchemy import create_engine
import psycopg2
from sqlalchemy import create_engine, text
##############################################################################################################################
SHORT_TERM_CUTOFF = 120  # months; only used as a last-resort fallback, see PORTFOLIO_DEFAULTS
MAX_MATRIX_CELLS = 20_000_000  # memory-safety cap  

PLOT_METRIC = "yield_percent" #yield_percent or gross_yield_percent


n_points = 1_000_000
control_object_recordid='d10af4c9-dbb6-49c4-9cf3-2d7219972cbe'
##############################################################################################################################
duck_con = duckdb.connect("/mnt/34bc75ca-9453-4032-88f3-699d8994bd14/DuckDb/localized.duckdb")
m910 = create_engine("postgresql+psycopg2://postgres:pass123$@192.168.1.210:5432/sandbox")
save_path_visual = "/home/dad/Documents/Python_Projects/visuals/modeling_risk/stage/1.0/"
save_name_visual = "mortgage_template.png"
full_path = save_path_visual + save_name_visual
##############################################################################################################################
curve_control = f"""
select * from python.yield_heatmap_loan_type_presets
where record_id='{control_object_recordid}'
"""
control_df = pd.read_sql(curve_control,m910)

min_fee = control_df['fee_min'].iloc[0]
max_fee = control_df['fee_max'].iloc[0]
fee_list = np.linspace(min_fee, max_fee, 50)
LOAN_TYPE = control_df['alias'].iloc[0]  

apr_range = (float(control_df['apr_min'].iloc[0]), float(control_df['apr_max'].iloc[0]))
risk_range = (float(control_df['pd_min'].iloc[0]), float(control_df['pd_max'].iloc[0]))
lgd = float(control_df['lgd'].iloc[0])

PRESETS = {
    LOAN_TYPE: dict(
        terms=np.array(control_df['term_options'].iloc[0]),
        apr_range=apr_range,
        risk_range=risk_range,
        lgd=lgd,
        principal_range=(float(control_df['principal_min'].iloc[0]), float(control_df['principal_max'].iloc[0])),
    ),
}

# --------------------------------------------------------------------------------
# SUBVENTION PROGRAMS -- any number of named tiers, each gated by its own PD
# band. Same underlying mechanic (someone pays the gap between the customer's
# rate and what the lender actually needs) but different tiers exist for very
# different reasons:
#   - super-prime buydowns: risk-driven, near-zero PD, OEM/securitization economics
#   - subprime buydowns: demand-driven (move volume/inventory), smaller and
#     shorter-lived discounts, NOT the same 0.9%-style teaser rate
#
# pd_min/pd_max define who's eligible for a given tier. Add, remove, or disable
# (enabled=False) tiers independently.
# --------------------------------------------------------------------------------
SUBVENTION_PROGRAMS = [
    dict(
        loan_type="auto", name="super_prime_buydown", enabled=False,
        pd_min=0.00, pd_max=0.03,
        advertised_apr=0.009,      # the 0.9% the customer sees
        target_yield_pct=4.0,      # lender still needs to net this
    ),
    # PLACEHOLDER -- fill in with real numbers from your own experience, not mine.
    # I don't have a reliable basis for what a subprime demand-pull discount or
    # its target yield actually look like in practice; these are just filled-in
    # markers so the structure runs, not a recommendation.
    dict(
        loan_type="auto", name="subprime_demand_pull", enabled=False,
        pd_min=0.15, pd_max=0.25,
        advertised_apr=0.06,       # PLACEHOLDER
        target_yield_pct=6.0,      # PLACEHOLDER
    ),
]

selected = [LOAN_TYPE]  # curve_control returns exactly one loan_type per record_id

term_chunks, principal_chunks, risk_chunks, lgd_chunks, apr_chunks, type_chunks = [], [], [], [], [], []
for name in selected:
    cfg = PRESETS[name]
    n_chunk = n_points // len(selected)
    term_chunks.append(np.random.choice(cfg["terms"], n_chunk))
    principal_chunks.append(np.random.uniform(*cfg["principal_range"], n_chunk))
    risk_chunks.append(np.random.uniform(*cfg["risk_range"], n_chunk))
    lgd_chunks.append(np.full(n_chunk, cfg["lgd"]))
    apr_chunks.append(np.random.uniform(*cfg["apr_range"], n_chunk))
    type_chunks.append(np.full(n_chunk, name))

term_vec = np.concatenate(term_chunks)
principal = np.concatenate(principal_chunks)
risks = np.concatenate(risk_chunks)
lgd_by_loan = np.concatenate(lgd_chunks)
aprs = np.concatenate(apr_chunks)
loan_type_vec = np.concatenate(type_chunks)  # tracks which preset each loan came from, by name
n_points = term_vec.size  # in case n_points wasn't evenly divisible by len(selected)

fees = np.random.choice(fee_list, n_points)

# Apply subvention program eligibility: for loans of a subvented type whose PD
# falls in that program's band, replace their market-sampled APR with the
# advertised promotional rate. Everyone else keeps the normal market-priced APR.
is_subvented = np.zeros(n_points, dtype=bool)
subvention_program_name = np.full(n_points, "", dtype=object)
for prog in SUBVENTION_PROGRAMS:
    if not prog.get("enabled", False):
        continue
    mask = (
        (loan_type_vec == prog["loan_type"])
        & (risks >= prog["pd_min"]) & (risks <= prog["pd_max"])
    )
    aprs[mask] = prog["advertised_apr"]
    is_subvented[mask] = True
    subvention_program_name[mask] = prog["name"]


# =====================================================================================
# DEFAULT-TIMING CURVE
# =====================================================================================
def default_profile(term):
    """
    Returns a (term+1,)-length array of FRACTIONS (summing to 1 over months 1..term)
    describing when, over the life of the loan, defaults happen.

    - term < 10yr : all default risk realized in year 1 (uniform across months 1..min(12,term))
    - term >= 10yr: stair-step -> 60% in yrs 1-3, 25% in yrs 3-7, 15% after yr 7.
      (month breakpoints 36/84 only make sense once term > 84, which is guaranteed
      here since this branch only runs for term >= 120)
    """
    prof = np.zeros(term + 1)
    if term < SHORT_TERM_CUTOFF:
        first_year = min(12, term)
        prof[1:first_year + 1] = 1.0 / first_year
    else:
        prof[1:37] = 0.60 / 36
        prof[37:85] = 0.25 / 48
        prof[85:term + 1] = 0.15 / (term - 84)
    prof /= prof.sum()  # defensive normalize
    return prof


# =====================================================================================
# YIELD CALC -- vectorized by unique term (huge speedup vs. per-loan python loop).
# Within each term group we also batch loans, because a (n_loans, term+1) matrix
# for a 30yr mortgage (361 months) at full 450K scale is 5+ GB across the working
# arrays -- batching keeps memory bounded regardless of term length or dataset size.
# =====================================================================================
MAX_MATRIX_CELLS = 200_000_000  # cap on (batch_size * (term+1)) per chunk


def yield_curve_vec(principal, fee, term_months, pd_arr, apr, lgd_arr, subvention=None):
    yield_percent = np.zeros_like(fee, dtype=float)
    if subvention is None:
        subvention = np.zeros_like(fee, dtype=float)

    for term in np.unique(term_months):
        mask = term_months == term
        idx = np.where(mask)[0]
        n = int(term)

        batch_size = max(1, MAX_MATRIX_CELLS // (n + 1))

        for start in range(0, idx.size, batch_size):
            chunk = idx[start:start + batch_size]

            apr_g = apr[chunk]
            pd_g = pd_arr[chunk]
            principal_g = principal[chunk]
            fee_g = fee[chunk]
            lgd_g = lgd_arr[chunk]
            subvention_g = subvention[chunk]

            r_m = apr_g / 12
            t = np.arange(n + 1)  # 0..n

            payment = (r_m * (1 + r_m) ** n) / ((1 + r_m) ** n - 1)  # (b,)

            # closed-form remaining balance fraction at every month, vectorized:
            # B(t) = (1+r_m)^t - payment * ((1+r_m)^t - 1) / r_m   (equivalent to the
            # recursive B[t] = B[t-1]*(1+r_m) - payment used in your originals)
            growth = (1 + r_m)[:, None] ** t[None, :]                  # (b, n+1)
            B = growth - payment[:, None] * (growth - 1) / r_m[:, None]
            B[:, 0] = 1.0

            # cumulative interest collected through month t = cumulative payments - cumulative principal paid
            interest_cum = payment[:, None] * t[None, :] - (1 - B)     # (b, n+1)

            prof = default_profile(n)               # (n+1,) shape identical for every loan with this term
            p = pd_g[:, None] * prof[None, :]        # (b, n+1) -- each loan's own PD scales the shared shape

            survive = 1 - pd_g

            exp_interest = (
                np.sum(p[:, 1:n + 1] * interest_cum[:, 1:n + 1], axis=1)
                + survive * interest_cum[:, n]
            )
            exp_loss = np.sum(p[:, 1:n + 1] * B[:, 1:n + 1] * lgd_g[:, None], axis=1)

            total_margin = principal_g * (exp_interest - exp_loss) - fee_g + subvention_g
            # annualized yield -- this is the fix for the CPU file's bug
            yield_percent[chunk] = (total_margin / principal_g / (n / 12)) * 100

    return yield_percent


def gross_yield_vec(term_months, apr):
    """
    Replicates a lender's typical reported 'Yield': Annualized Finance Charge /
    Average Net Principal Balance. NOT risk-adjusted -- no PD, no LGD, no fee.
    Purely the accrual rate a loan earns on its own average outstanding balance.
    For a fixed-rate amortizing loan this converges almost exactly to the APR
    itself, since interest each period is just rate x current balance -- that's
    why this is the right metric to compare against a "gross Yield" target from
    an internal report, and yield_percent (above) is not.
    """
    gross_yield = np.zeros_like(apr, dtype=float)
    for term in np.unique(term_months):
        mask = term_months == term
        idx = np.where(mask)[0]
        n = int(term)
        apr_g = apr[idx]
        r_m = apr_g / 12
        t = np.arange(n + 1)
        payment = (r_m * (1 + r_m) ** n) / ((1 + r_m) ** n - 1)
        growth = (1 + r_m)[:, None] ** t[None, :]
        B = growth - payment[:, None] * (growth - 1) / r_m[:, None]
        B[:, 0] = 1.0
        interest_cum = payment[:, None] * t[None, :] - (1 - B)
        total_interest = interest_cum[:, n]
        avg_balance = B[:, :-1].mean(axis=1)
        gross_yield[idx] = (total_interest / avg_balance / (n / 12)) * 100
    return gross_yield


print(f"Calculating yields for {n_points:,} data points ({', '.join(selected)}) "
      f"across {len(np.unique(term_vec))} term buckets...")

# Pass 1: yield as the customer/loan-on-paper would show it -- at the advertised
# APR, with no subvention money added yet.
yield_before_subvention = yield_curve_vec(principal, fees, term_vec, risks, aprs, lgd_by_loan)

# How much would the OEM need to pay, per loan, to bring an eligible loan up to
# its program's target yield? Only applies where a shortfall actually exists --
# never a negative (clawback) number.
subvention = np.zeros(n_points)
for prog in SUBVENTION_PROGRAMS:
    if not prog.get("enabled", False):
        continue
    mask = subvention_program_name == prog["name"]
    years = term_vec[mask] / 12
    target_margin = prog["target_yield_pct"] / 100 * principal[mask] * years
    current_margin = yield_before_subvention[mask] / 100 * principal[mask] * years
    subvention[mask] = np.maximum(target_margin - current_margin, 0.0)

# Pass 2: final yield, now including the subvention payment where it applies.
yield_vec = yield_curve_vec(principal, fees, term_vec, risks, aprs, lgd_by_loan, subvention=subvention)

# Gross yield -- not risk-adjusted at all, matches a lender's typical reported
# "Yield" (finance charge / average balance). Compare THIS to a report like
# your company's, not yield_percent -- they're measuring different things.
gross_yield_vec_result = gross_yield_vec(term_vec, aprs)

df = pd.DataFrame({
    'apr': aprs, 'risk': risks, 'fee': fees, 'term': term_vec, 'loan_type': loan_type_vec,
    'is_subvented': is_subvented, 'subvention_program': subvention_program_name, 'subvention': subvention,
    'yield_before_subvention': yield_before_subvention, 'yield_percent': yield_vec,
    'gross_yield_percent': gross_yield_vec_result,
})

print("\nOverall yield stats:")
print(f"  Min: {yield_vec.min():.2f}%  Max: {yield_vec.max():.2f}%  Mean: {yield_vec.mean():.2f}%")

if is_subvented.any():
    for prog_name in df.loc[df.is_subvented, 'subvention_program'].unique():
        sv = df[df.subvention_program == prog_name]
        print(f"\nSubvention tier '{prog_name}': n={len(sv):,}")
        print(f"  Mean APR seen by customer: {sv.apr.mean()*100:.2f}%")
        print(f"  Mean yield WITHOUT subvention: {sv.yield_before_subvention.mean():.2f}%")
        print(f"  Mean subvention paid per loan: ${sv.subvention.mean():,.0f}")
        print(f"  Mean yield WITH subvention (lender's real economics): {sv.yield_percent.mean():.2f}%")

for name in selected:
    sub = df[df.loan_type == name]
    print(f"\n{name}: n={len(sub):,}")
    print(f"  Mean gross yield (matches a 'Yield' report): {sub.gross_yield_percent.mean():.2f}%")
    print(f"  Mean net yield (risk-adjusted, this model's yield_percent): {sub.yield_percent.mean():.2f}%   "
          f"PD range used: {sub.risk.min()*100:.2f}%-{sub.risk.max()*100:.2f}%")
    for term in sorted(sub.term.unique()):
        g = sub[sub.term == term]
        print(f"    term={int(term):3d}mo  mean yield={g.yield_percent.mean():6.2f}%")

# sanity check: same apr/pd/fee/principal, different term -> annualized yield should be ~flat now
print("\nSanity check (fixed apr=0.12, pd=0.03, fee=800, principal=18000; short-term buckets only):")
for term in [36, 48, 60, 72, 84, 96, 108]:
    y = yield_curve_vec(
        np.array([18000.0]), np.array([800.0]), np.array([term]),
        np.array([0.03]), np.array([0.12]), np.array([0.65])
    )
    print(f"  term={term:3d}mo  annualized yield={y[0]:.2f}%")

# =====================================================================================
# PLOTTING -- one panel per selected loan type (any number). Each panel uses
# ITS OWN preset's apr_range/risk_range as the axis -- still fixed by hand
# (never derived from the sampled data), but no longer forced onto one shared
# scale that products with non-overlapping ranges (mortgage vs personal loan)
# can't both use well. Same preset -> same axis, every run, regardless of seed
# or point count -- that part hasn't changed.
# =====================================================================================
print("\nCreating heatmaps...")

PANEL_WIDTH_IN = 18   # inches, per panel (was 9 -> this is 4x)
FIG_HEIGHT_IN = 12    # inches, fixed regardless of how many panels

panel_specs = [(name, df[df.loan_type == name]) for name in selected]

fig, axes = plt.subplots(
    1, len(panel_specs),
    figsize=(PANEL_WIDTH_IN * len(panel_specs), FIG_HEIGHT_IN),
    dpi=150, squeeze=False,
)
axes = axes[0]

for (title, sub), ax in zip(panel_specs, axes):
    cfg = PRESETS[title]
    xedges = np.linspace(*cfg["apr_range"], 80)
    yedges = np.linspace(*cfg["risk_range"], 80)

    metric_label = "Gross Yield (%)" if PLOT_METRIC == "gross_yield_percent" else "Net Annualized Yield (%)"

    heatmap, _, _ = np.histogram2d(sub['apr'], sub['risk'], bins=[xedges, yedges], weights=sub[PLOT_METRIC])
    counts, _, _ = np.histogram2d(sub['apr'], sub['risk'], bins=[xedges, yedges])
    with np.errstate(invalid='ignore'):
        heatmap = heatmap / counts
    heatmap[counts == 0] = np.nan  # no data here -> blank, not a misleading "0% yield"

    # color scale reacts to what's actually on the panel (post-binning), not a
    # formula projected off apr_range/risk_range/lgd -- fees, amortization, and
    # subvention all shift real yields away from that theoretical bound.
    color_range = (np.nanmin(heatmap), np.nanmax(heatmap))

    cmap = plt.get_cmap('RdYlGn').copy()
    cmap.set_bad(color='white')

    im = ax.imshow(
        heatmap.T, origin='lower', aspect='auto',
        extent=[xedges.min() * 100, xedges.max() * 100, yedges.min() * 100, yedges.max() * 100],
        cmap=cmap, vmin=color_range[0], vmax=color_range[1],
    )
    cbar = fig.colorbar(im, ax=ax, label=metric_label)
    cbar.ax.tick_params(labelsize=16)
    cbar.set_label(metric_label, fontsize=18)
    ax.set_xlabel('APR (%)', fontsize=20)
    ax.set_ylabel('PD (%)', fontsize=20)
    ax.set_title(f'{title} ({metric_label})', fontsize=24)
    ax.tick_params(labelsize=16)

plt.tight_layout()
plt.savefig('/home/dad/Documents/Python_Projects/visuals/modeling_risk/stage/1.0/yield_heatmap_preview_test.png')
print("Done!")