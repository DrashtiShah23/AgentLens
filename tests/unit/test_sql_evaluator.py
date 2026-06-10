from observatory.evaluation.sql_evaluator import SqlEvaluator


def test_valid_sql_scores_high():
    ev = SqlEvaluator()
    result = ev.evaluate({
        "generated_sql": "SELECT SUM(revenue) FROM revenue_daily",
        "final_answer": "125000",
        "expected_answer": "125000",
    })
    assert result.score == 1.0


def test_syntax_error_scores_zero():
    ev = SqlEvaluator()
    result = ev.evaluate({
        "generated_sql": "SELECT SUM(revenue) FORM revenue_daily",
    })
    assert result.score == 0.0


def test_destructive_sql_blocked():
    ev = SqlEvaluator()
    result = ev.evaluate({
        "generated_sql": "DROP TABLE revenue_daily",
    })
    assert result.score == 0.0
    assert "destructive" in result.notes


def test_empty_sql_scores_zero():
    ev = SqlEvaluator()
    result = ev.evaluate({"generated_sql": ""})
    assert result.score == 0.0
