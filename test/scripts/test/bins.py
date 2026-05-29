import numpy as np
import matplotlib.pyplot as plt

class DemoBinner:
    def __init__(self, d_clean):
        self.d_clean = d_clean
        self.bins = None

    def build_bins(self, n_bins=100, dmin=None, dmax=None, alpha=2.0):
        """
        Smooth nonlinear binning using power-law stretching.
        alpha > 1 → more resolution at large distances (log-like)
        alpha = 1 → linear
        alpha < 1 → more resolution at small distances
        """
        if dmin is None:
            dmin = max(1e-3, self.d_clean.min())
        if dmax is None:
            dmax = self.d_clean.max()

        u = np.linspace(0, 1, n_bins)
        bins = dmin + (dmax - dmin) * (u ** alpha)

        self.bins = bins
        return self.bins

# Simulated distance data
np.random.seed(0)
distances = np.random.rand(200) * 100  # distances between 0 and 100

binner = DemoBinner(distances)

# Different alpha values to test
alphas = [0.5, 1.0, 2.0, 5.0]

plt.figure(figsize=(8,5))

for alpha in alphas:
    bins = binner.build_bins(n_bins=50, alpha=alpha)
    plt.plot(bins, np.arange(len(bins)), label=f'alpha={alpha}')

plt.xlabel('Distance')
plt.ylabel('Bin index')
plt.title('Effect of alpha on power-law binning')
plt.legend()
plt.grid(True)
plt.show()