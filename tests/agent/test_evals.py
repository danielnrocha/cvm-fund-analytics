from collections import Counter

from agent.evals import load_cases, summarize


def test_versioned_dataset_has_disjoint_families_and_three_variants():
    development, dev_hash = load_cases("development")
    holdout, holdout_hash = load_cases("holdout")
    assert len(development) == 72
    assert len(holdout) == 48
    assert not {case.family for case in development} & {case.family for case in holdout}
    assert set(Counter(case.family for case in development + holdout).values()) == {3}
    assert dev_hash != holdout_hash


def test_summary_does_not_count_unrun_oracles_as_successes():
    result = summarize([
        {"exact": True, "supported": True, "critical": True, "oracle_exact": True},
        {"exact": False, "supported": True, "critical": True},
        {"exact": True, "supported": False, "critical": False},
    ])
    assert result == {
        "exact": {"passed": 2, "trials": 3},
        "supported": {"passed": 1, "trials": 2},
        "critical": {"passed": 1, "trials": 2},
        "numeric_oracle": {"passed": 1, "trials": 1},
    }
