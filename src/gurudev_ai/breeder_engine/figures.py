"""Publication-ready evidence graphics, faithfully labelled as INTERNAL validation."""
from pathlib import Path
import numpy as np
import pandas as pd


def generate_evidence_figures(output: Path, predictions: pd.DataFrame,
                              candidates: pd.DataFrame, metric: dict, trait: str,
                              direction: str) -> list[str]:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12,
                        'axes.titlesize': 13, 'figure.dpi': 150,
                        'savefig.dpi': 350, 'pdf.fonttype': 42, 'svg.fonttype':'none'})
    x = predictions['observed'].to_numpy(dtype=float)
    y = predictions['predicted'].to_numpy(dtype=float)
    lo, hi = float(min(x.min(),y.min())), float(max(x.max(),y.max()))
    expansion = .06 * max(hi-lo,1e-3)
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    ax.scatter(x,y,alpha=.75,edgecolors='white',s=50,linewidths=.4,label=f'Out-of-fold predictions (n={len(x)})')
    ax.plot([lo-expansion,hi+expansion],[lo-expansion,hi+expansion],ls='--',color='0.4',label='Perfect agreement (1:1)')
    ax.set_xlim(lo-expansion,hi+expansion);ax.set_ylim(lo-expansion,hi+expansion)
    ax.set_xlabel(f'Observed {trait} (original trait units)')
    ax.set_ylabel(f'Predicted {trait} (original trait units)')
    ax.set_title('A | Internal cross-validated GBLUP')
    ax.text(.03,.97,f"Nested-CV RMSE = {metric['rmse']:.3f}\nR² = {metric['r2']:.3f}\nPearson r = {metric['pearson_r']}",
            transform=ax.transAxes,va='top',ha='left',bbox=dict(facecolor='white',alpha=.8,edgecolor='.8'))
    ax.legend(loc='lower right',fontsize=9)
    fig.tight_layout(); fig.savefig(output/'A_GBLUP_nested_CV.png',dpi=350)
    fig.savefig(output/'A_GBLUP_nested_CV.pdf');plt.close(fig)

    table = candidates.loc[candidates['genotype_qc_pass'] &
             (candidates['prediction_type']=='unphenotyped_candidate')].copy()
    saved=['A_GBLUP_nested_CV.png','A_GBLUP_nested_CV.pdf']
    if len(table):
        table = table.sort_values('prediction',ascending=(direction=='min')).head(20)
        fig,ax=plt.subplots(figsize=(8.5,max(4.3,len(table)*.38+.8)))
        yaxis = np.arange(len(table))
        ax.barh(yaxis,table['prediction'].to_numpy(float))
        ax.set_yticks(yaxis,table['sample_id'].tolist());ax.invert_yaxis()
        ax.set_xlabel(f'Model-predicted {trait} (original trait units)')
        ax.set_title('B | Unphenotyped candidate predictions (in-population model)')
        ax.xaxis.set_major_locator(MaxNLocator(6))
        fig.text(.02,.01,'Prediction uncertainty and external validity not established; ranking is exploratory.',fontsize=9)
        fig.tight_layout(rect=(0,.035,1,1))
        fig.savefig(output/'B_Unphenotyped_candidates.png',dpi=350)
        fig.savefig(output/'B_Unphenotyped_candidates.pdf');plt.close(fig)
        saved.extend(['B_Unphenotyped_candidates.png','B_Unphenotyped_candidates.pdf'])
    return saved
