import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.labelsize': 8, 'axes.titlesize': 8.5,
    'legend.fontsize': 7, 'xtick.labelsize': 7, 'ytick.labelsize': 7, 'lines.linewidth': 1.4,
    'axes.grid': True, 'grid.alpha': 0.25, 'grid.linewidth': 0.5, 'axes.spines.top': False,
    'axes.spines.right': False, 'figure.dpi': 120, 'savefig.dpi': 300, 'savefig.bbox': 'tight',
    'axes.prop_cycle': matplotlib.cycler(color=PAL), 'legend.frameon': False,
})
COL1 = 3.5   # IEEE single column width [in]
COL2 = 7.16  # double column
