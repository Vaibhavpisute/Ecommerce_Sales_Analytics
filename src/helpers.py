"""Small helpers shared by scripts."""

# Brazilian regions (same mapping as in sql/q15_order_value_by_payment_and_region.sql)
REGION_STATES = {
    "North": "AC AP AM PA RO RR TO",
    "Northeast": "AL BA CE MA PB PE PI RN SE",
    "Central-West": "DF GO MT MS",
    "Southeast": "ES MG RJ SP",
    "South": "PR RS SC",
}
STATE_TO_REGION = {s: region for region, states in REGION_STATES.items() for s in states.split()}
