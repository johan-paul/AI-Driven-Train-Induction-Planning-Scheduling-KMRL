# core/branding_optimizer.py
from typing import List, Dict, Any
import numpy as np
import pandas as pd
import pulp
from .ml_model import predict_failure_prob

# finite-difference step (hours) to estimate marginal benefit
FD_STEP = 1.0

def _prepare_features_for_model(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure required columns for ML model exist and are numeric.
    Model expects:
    ['days_to_cert','jobcard_severity','odometer_km','last_clean_days','stabling_index',
     'branding_shortfall','vibration','temp','humidity']
    """
    expected = ['days_to_cert','jobcard_severity','odometer_km','last_clean_days','stabling_index',
                'branding_shortfall','vibration','temp','humidity']
    X = df.copy()
    for c in expected:
        if c not in X.columns:
            X[c] = 0.0
    X = X[expected].astype(float)
    return X

def estimate_marginal_value_per_hour(df_rows: List[Dict[str,Any]], per_train_capacity: int = None) -> pd.DataFrame:
    """
    For each train row, estimate marginal reduction in failure-probability per 1 branding hour.
    Input: list of dict rows (each row must include fields used by ML model).
    Returns DataFrame with columns:
      ['train_id','req','done','current_prob','prob_after_1h','marginal_value_per_hour']
    Notes:
      - If train has advertiser=None or req==0 we give marginal_value=0.
      - per_train_capacity can cap the FD_STEP (e.g. do not allocate more than remaining req).
    """
    df = pd.DataFrame(df_rows).copy()
    # canonical columns
    df['train_id'] = df.get('train_id')
    df['req'] = df.get('branding_req_hours').fillna(0).astype(int)
    df['done'] = df.get('branding_done').fillna(0).astype(int)
    # current shortfall = req - done (>=0)
    df['shortfall'] = (df['req'] - df['done']).clip(lower=0).astype(int)

    # build features for model baseline
    # the ML model expects 'branding_shortfall' as a feature; use shortfall
    feat_base = _prepare_features_for_model(df.assign(branding_shortfall=df['shortfall']))
    current_probs = predict_failure_prob(feat_base)

    # for each train, reduce shortfall by FD_STEP (simulating allocating 1 hour) but not below 0
    df_fd = df.copy()
    # effective 1-hour reduction can't exceed current shortfall
    one_step = min(FD_STEP, 1.0)
    df_fd['shortfall_after'] = (df_fd['shortfall'] - one_step).clip(lower=0)
    feat_after = _prepare_features_for_model(df_fd.assign(branding_shortfall=df_fd['shortfall_after']))
    after_probs = predict_failure_prob(feat_after)

    df['current_prob'] = current_probs
    df['prob_after_1h'] = after_probs
    # marginal benefit = reduction in p_fail per hour
    df['marginal_value_per_hour'] = (df['current_prob'] - df['prob_after_1h']) / one_step
    # guard negatives -> set to 0 (if model increases risk after allocating an hour, treat as 0)
    df.loc[df['marginal_value_per_hour'] < 0, 'marginal_value_per_hour'] = 0.0

    # If no advertiser or req==0 -> zero value
    adv_missing = df.get('advertiser').isna() | (df.get('advertiser') == '') | (df.get('advertiser') == 'None')
    df.loc[adv_missing, 'marginal_value_per_hour'] = 0.0
    df.loc[df['shortfall'] == 0, 'marginal_value_per_hour'] = 0.0

    return df[['train_id','req','done','shortfall','current_prob','prob_after_1h','marginal_value_per_hour']]

def allocate_branding_hours(df_rows: List[Dict[str,Any]], total_hours_available: int) -> pd.DataFrame:
    """
    Compute integer allocation (hours) across trains to best reduce weighted failure probability.
    Strategy:
      - Use marginal_value_per_hour as a per-hour weight (higher => more valuable)
      - Decision variables x_i ∈ {0..shortfall_i} (integer hours allocated to train i)
      - Objective: maximize sum_i (marginal_value_per_hour_i * x_i)
        -> Equivalent to minimize negative. We implement maximization.
      - Constraint: sum_i x_i <= total_hours_available
    Returns DataFrame with allocation results appended: ['alloc','after_done','after_shortfall']
    """
    # estimate marginal values
    df_vals = estimate_marginal_value_per_hour(df_rows)
    # join original rows (to preserve advertiser etc)
    df = pd.DataFrame(df_rows).set_index('train_id').join(df_vals.set_index('train_id'), how='left').reset_index()
    df['shortfall'] = df['shortfall'].fillna(0).astype(int)
    df['marginal_value_per_hour'] = df['marginal_value_per_hour'].fillna(0.0).astype(float)

    # build ILP (maximize sum value * alloc)
    prob = pulp.LpProblem("branding_alloc_max", pulp.LpMaximize)
    alloc_vars = {}
    for i, row in df.iterrows():
        tid = row['train_id']
        ub = int(row['shortfall'])
        # create integer variable x_tid (0..ub)
        alloc_vars[tid] = pulp.LpVariable(f"x_{tid}", lowBound=0, upBound=ub, cat='Integer')

    # objective
    prob += pulp.lpSum([row['marginal_value_per_hour'] * alloc_vars[row['train_id']] for _, row in df.iterrows()])

    # budget constraint
    prob += pulp.lpSum([alloc_vars[row['train_id']] for _, row in df.iterrows()]) <= int(total_hours_available)

    # solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    # read allocations
    df['alloc'] = df['train_id'].apply(lambda tid: int(pulp.value(alloc_vars[tid]) or 0))
    df['after_done'] = df['done'] + df['alloc']
    df['after_shortfall'] = (df['req'] - df['after_done']).clip(lower=0)

    # helpful metrics
    df['value_allocated'] = df['marginal_value_per_hour'] * df['alloc']

    return df

