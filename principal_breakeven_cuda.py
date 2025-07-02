import cupy as cp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#Parameters
#           |\---/|
#           | o_o |
#            \_^_/
n_points = 3000000
#   this governs how fast and how detailed the heat map is
#   for your first test you should limit the value at around 100,000
#   3m points is about 4 gigs of vram, so the ceiling of most lower-end cuda cards. 

fee_list = cp.linspace(1, 3000, 50)
#   This is the list of fees that are unrelated to the asset price 
#   In my editorials its about the SG&A

risk_list = cp.linspace(0.01, 0.08, 60)
#   this is a strata of loan loss reserves on a portfolio 
#   you can find this by (accounts of doubtful collection) / (gross accounts reciable)
#   its a measure of how much of the portfolio that would be in default in that moment

terms = cp.array([48, 60, 72])
#   car note in months 

front_loads = cp.linspace(0.05, 0.08, 30)
#   We can see in some 10k reports that they describe the deliquency periods of their loans
#   we can see that a majority, ~70%, of loans enter in default in the first 8 months
#   This front load is the easiset way of adding a timing element to the portfolio 



#Generate random indices for each parameter (non-grid)
fees_idx = cp.random.randint(0, 50, size=n_points)
risks_idx = cp.random.randint(0, 50, size=n_points)
terms_idx = cp.random.randint(0, 4, size=n_points)
front_idx = cp.random.randint(0, 10, size=n_points)

fees = fee_list[fees_idx]
risks = risk_list[risks_idx]
term_vec = terms[terms_idx]
front_vec = front_loads[front_idx]

def break_even_principal_vec(fee_amount, apr, term_months, pd, front_load_frac):
    # fee_amount, term_months, pd, front_load_frac are all (n_points,) arrays
    r_m = apr / 12
    n = term_months  # (n_points,)
    payment = (r_m * cp.power(1 + r_m, n)) / (cp.power(1 + r_m, n) - 1)
    # Need to build schedules for each unique n; here, assume all n are equal or just use max(n)
    n_max = int(cp.asnumpy(n).max())
    B = cp.zeros((fee_amount.size, n_max + 1))
    B[:, 0] = 1.0
    for t in range(1, n_max + 1):
        B[:, t] = B[:, t - 1] * (1 + r_m) - payment
    # Default-time PDF
    p = cp.zeros((fee_amount.size, n_max + 1))
    for i in range(fee_amount.size):
        ten = min(11, n[i] + 1)
        p[i, 1:ten] = pd[i] * front_load_frac[i] / (ten - 1)
        if n[i] >= 10:
            p[i, 11:] = pd[i] * (1 - front_load_frac[i]) / (n[i] - 10)
    survive = 1 - pd
    interest_if_default = payment[:, None] * cp.arange(n_max + 1) - (1 - B)
    exp_interest = cp.sum(p[:, 1:] * interest_if_default[:, 1:], axis=1) + survive * interest_if_default[:, -1]
    exp_loss = cp.sum(p[:, 1:] * B[:, 1:], axis=1)
    margin = exp_interest - exp_loss
    break_even = cp.where(margin > 0, fee_amount / margin, cp.nan)
    return break_even

be_vec = break_even_principal_vec(fees, apr=0.07, term_months=term_vec, pd=risks, front_load_frac=front_vec)
# Move data back to CPU for pandas and plotting
df = pd.DataFrame({
    'fee': cp.asnumpy(fees),
    'risk': cp.asnumpy(risks),
    'break_even_principal': cp.asnumpy(be_vec)
})
df = df[(df['break_even_principal'] > 0) & (df['break_even_principal'] < 60000)].reset_index(drop=True)
print(df.head())
heatmap = df.pivot_table(index='risk', columns='fee', values='break_even_principal')

plt.figure(figsize=(12, 7))
plt.imshow(heatmap, aspect='auto', origin='lower',
           cmap='RdYlGn_r', extent=[
               heatmap.columns.min(), heatmap.columns.max(),
               heatmap.index.min(), heatmap.index.max()
           ])
plt.colorbar(label='Break-even Principal')
plt.xlabel('Fee')
plt.ylabel('Risk')
plt.title('Break-even Principal Heatmap (Fee vs Risk)')
plt.tight_layout()
plt.show()
