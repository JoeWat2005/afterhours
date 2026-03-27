# Route Services

## Safety Estimator

Scores route safety using empirical Bayes. Blends a baseline harm rate with observed police/user report data so routes with sparse data get sensible scores instead of misleading ones. More data means less reliance on the baseline.

Adjusted for time of day (late night is riskier) and lighting (poor or unknown lighting inflates risk).

Outputs an `expected_harm_rate`, a `serious_incident_probability`, and a 0-1 `safety_score` that feeds into route ranking. Config lives in `app/core/route_risk_config.py`.