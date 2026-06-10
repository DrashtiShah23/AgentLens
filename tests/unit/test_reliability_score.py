from observatory.evaluation.overall_score import OverallScoreCalculator


def test_missing_scores_excluded_not_zero():
    calc = OverallScoreCalculator()
    score = calc.compute("text_to_sql", {
        "correctness": 0.8,
        "sql": None,
        "tool": None,
        "retrieval": None,
        "format": 1.0,
        "latency": 1.0,
        "cost": 1.0,
    })
    assert score > 0.8
    assert score <= 1.0


def test_null_correctness_excluded():
    calc = OverallScoreCalculator()
    score = calc.compute("retrieval_qa", {
        "correctness": None,
        "sql": None,
        "tool": None,
        "retrieval": 0.9,
        "format": 1.0,
        "latency": 1.0,
        "cost": 1.0,
    })
    assert 0.9 <= score <= 1.0


def test_task_type_weight_boost():
    calc = OverallScoreCalculator()
    sql_score = calc.compute("text_to_sql", {
        "correctness": 0.5, "sql": 1.0, "tool": None, "retrieval": None,
        "format": 0.5, "latency": 1.0, "cost": 1.0,
    })
    other_score = calc.compute("summarization", {
        "correctness": 0.5, "sql": None, "tool": None, "retrieval": None,
        "format": 0.5, "latency": 1.0, "cost": 1.0,
    })
    assert sql_score != other_score
