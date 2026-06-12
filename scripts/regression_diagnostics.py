"""OLS regression with standard diagnostics and residual plots."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor


def ols_diagnostics(X, y, out_dir='outputs/diagnostics', add_const=True, hac_lags=1):
    """Fit OLS, print diagnostics, and save residual plots.

    Parameters
    ----------
    X : DataFrame or array of regressors
    y : Series or array, dependent variable
    out_dir : directory for plot output
    add_const : add intercept term
    hac_lags : Newey-West lag count (0 to skip HAC)
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    X_df = X.copy() if isinstance(X, (pd.DataFrame, pd.Series)) else pd.DataFrame(X)
    X_design = sm.add_constant(X_df) if add_const else X_df

    model = sm.OLS(y, X_design).fit()
    print(model.summary())

    if hac_lags and hac_lags > 0:
        try:
            hac_res = model.get_robustcov_results(cov_type='HAC', maxlags=hac_lags)
            print('\nHAC robust standard errors (Newey-West):')
            print(hac_res.summary())
        except Exception as e:
            print('HAC robust covariance failed:', e)

    dw = durbin_watson(model.resid)
    print(f'Durbin-Watson: {dw:.3f}')

    bp_test = het_breuschpagan(model.resid, model.model.exog)
    bp_labels = ['Lagrange multiplier stat', 'p-value', 'f-value', 'f p-value']
    print('\nBreusch-Pagan test:')
    print(dict(zip(bp_labels, bp_test)))

    print('\nVariance Inflation Factors:')
    vif_df = pd.DataFrame({
        'variable': X_design.columns,
        'VIF': [variance_inflation_factor(X_design.values, i) for i in range(X_design.shape[1])],
    })
    print(vif_df)

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    axes[0, 0].scatter(model.fittedvalues, model.resid, alpha=0.7)
    axes[0, 0].axhline(0, color='k', linestyle='--')
    axes[0, 0].set(xlabel='Fitted', ylabel='Residual', title='Residuals vs Fitted')

    sm.graphics.qqplot(model.resid, line='45', ax=axes[0, 1])
    axes[0, 1].set_title('QQ Plot')

    axes[1, 0].hist(model.resid, bins=20)
    axes[1, 0].set_title('Residual Histogram')

    try:
        from statsmodels.graphics.tsaplots import plot_acf
        plot_acf(model.resid, ax=axes[1, 1], lags=20)
        axes[1, 1].set_title('Residual ACF')
    except Exception:
        axes[1, 1].text(0.1, 0.5, 'ACF plot unavailable')

    plt.tight_layout()
    out_plot = Path(out_dir) / 'residual_diagnostics.png'
    plt.savefig(out_plot)
    print(f"Saved residual diagnostics to {out_plot}")

    return model
