"""Simple bias analysis on PEP541 requests in the pypi/support repository.

Requires pep541_pred, this is pep541_pred from scrape_issue_data.py
with a column "pred" added, which contains a string encoding one of the
nine "regions of origin" as described in the README.md.

Subsets to issues that are still open, and carries out tabulation with:

* region of origin, versus
* seven-number summary including quartiles
* waiting time so far, since opening

A significance analysis is performed for the table at the end,
using the Kruskal-Wallis test for equality of waiting time distributions,
followed by Dunn's post-hoc test.
"""

from datetime import datetime
import pandas as pd

# load pep541_predictions

pep541_pred = pd.read_csv("path here")

result = pep541_pred.groupby("pred")["duration_D"].agg(['mean', "var"])
result = pep541_pred.groupby("pred")["duration_D"].describe()

today = pd.Timestamp(datetime.today().date())
pep541_pred.loc[pep541_pred.state=="open", "duration_D"] = (today - pep541_pred[pep541_pred.state=="open"]['created_at']).dt.days + 1

pep541_pred[pep541_pred.state=="open"].groupby("pred")["created_at"].describe()

# create table of waiting times
wait_df = pep541_pred[pep541_pred.state=="open"].groupby("pred")["duration_D"].describe()
wait_df.index.names = [None]
wait_df = wait_df.loc[:, ["50%", "25%", "75%", "max", "mean", "std", "count"]]

# table of waiting times
wait_df.round().sort_values(by=["50%"], ascending=True)[:-1]

# table of issue state vs region of origin
pd.crosstab(pep541_pred['pred'], pep541_pred["state"], normalize=0)


# Kruskal-Wallis test for significance of association in wait_df
import scikit_posthocs as sp

pep541_pred["closed"] = pep541_pred["state"] == "closed"
open_is = pep541_pred[pep541_pred.state=="open"]
open_is = open_is[-open_is.pred.isna()]

def kruskal_wallis_test(df, value_col, group_col):
    from scipy.stats import kruskal
    # Extract unique groups
    groups = df[group_col].unique()
    
    # Collect data for each group
    group_data = [df[df[group_col] == group].loc[:, value_col].values for group in groups]
    
    # Perform Kruskal-Wallis test
    h_statistic, p_value = kruskal(*group_data)
    
    return h_statistic, p_value

# Perform the test
h_statistic, p_value = kruskal_wallis_test(open_is, 'duration_D', 'pred')

print(f"Kruskal-Wallis H-statistic: {h_statistic}")
print(f"P-value: {p_value}")

# Dunn's post-hoc test
dunn_test = sp.posthoc_dunn(open_is, val_col='duration_D', group_col='pred')
