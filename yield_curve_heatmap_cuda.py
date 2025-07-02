import cupy as cp
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


n_points = 100000 # increase for higher density
apr_list = cp.linspace(0.05, 0.15, 12)
risk_list = cp.linspace(0.01, 0.08, 12)
fee_list = cp.linspace(1, 3000, 12)
terms = cp.array([48, 60, 72])
front_loads = cp.linspace(0.05, 0.08, 12)


principal = cp.random.uniform(25000, 35000, n_points)

# Random non-grid sampling
aprs = cp.random.uniform(0.05, 0.30, n_points)
risks = cp.random.uniform(0.01, 0.08, n_points)
fees = cp.random.choice(fee_list, n_points)
term_vec = cp.random.choice(terms, n_points)
front_vec = cp.random.choice(front_loads, n_points)

def yield_curve_vec(principal, fee, term_months, pd, front_load_frac, apr):
    # All inputs are vectors (n_points,)
    r_m = apr / 12
    n = term_months.astype(cp.int32)
    payment = (r_m * cp.power(1 + r_m, n)) / (cp.power(1 + r_m, n) - 1)
    n_max = int(cp.asnumpy(n).max())
    yield_percent = cp.zeros_like(fee)
    for i in range(fee.size):
        B = cp.zeros(n_max + 1)
        B[0] = 1.0
        for t in range(1, int(n[i]) + 1):
            B[t] = B[t - 1] * (1 + r_m[i]) - payment[i]
        p = cp.zeros(n_max + 1)
        ten = min(11, n[i] + 1)
        p[1:ten] = pd[i] * front_load_frac[i] / (ten - 1)
        if n[i] >= 10:
            p[11:n[i] + 1] = pd[i] * (1 - front_load_frac[i]) / (n[i] - 10)
        survive = 1 - pd[i]
        interest_if_default = payment[i] * cp.arange(n_max + 1) - (1 - B)
        exp_interest = cp.sum(p[1:n[i]+1] * interest_if_default[1:n[i]+1]) + survive * interest_if_default[n[i]]
        exp_loss = cp.sum(p[1:n[i]+1] * B[1:n[i]+1])
        total_margin = principal[i] * (exp_interest - exp_loss) - fee[i]
        yield_percent[i] = (total_margin / principal[i]) * 100
    return yield_percent

yield_vec = yield_curve_vec(
    principal=principal,
    fee=fees,
    term_months=term_vec,
    pd=risks,
    front_load_frac=front_vec,
    apr=aprs
)

# Back to CPU for plotting
df = pd.DataFrame({
    'apr': cp.asnumpy(aprs),
    'risk': cp.asnumpy(risks),
    'fee': cp.asnumpy(fees),
    'term': cp.asnumpy(term_vec),
    'yield_percent': cp.asnumpy(yield_vec)
})

# For a heatmap, bin into a 2D grid (APR vs RISK, mean yield in each cell)
xedges = np.linspace(df['apr'].min(), df['apr'].max(), 100)
yedges = np.linspace(df['risk'].min(), df['risk'].max(), 100)
heatmap, _, _ = np.histogram2d(
    df['apr'], df['risk'], bins=[xedges, yedges],
    weights=df['yield_percent']
)
counts, _, _ = np.histogram2d(
    df['apr'], df['risk'], bins=[xedges, yedges]
)
heatmap = np.divide(heatmap, counts, out=np.zeros_like(heatmap), where=counts != 0)

plt.figure(figsize=(12, 7))
plt.imshow(
    heatmap.T,
    origin='lower',
    aspect='auto',
    extent=[xedges.min()*100, xedges.max()*100, yedges.min()*100, yedges.max()*100],
    cmap='RdYlGn',
    vmin=0,
    vmax=20
)

plt.xlim(left=xedges.min()*100, right=20)  
plt.colorbar(label='Yield (%)')
plt.xlabel('APR (%)')
plt.ylabel('Risk (%)')
plt.title('Yield Curve Heatmap (Random CUDA Cloud)')
plt.tight_layout()
plt.show()
