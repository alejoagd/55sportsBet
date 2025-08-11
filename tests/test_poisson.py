from src.poisson.compute import outcome_probs

def test_probs_sum_to_one():
    h,d,a = outcome_probs(1.4,1.1)
    assert abs((h+d+a) - 1.0) < 1e-6