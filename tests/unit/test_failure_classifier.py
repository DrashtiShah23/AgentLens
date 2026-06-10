from observatory.classification.failure_classifier import FailureClassifier


def test_sql_failure_classification():
    clf = FailureClassifier()
    result = clf.classify({
        "task_type": "text_to_sql", "sql_score": 0.0, "overall_score": 0.3,
        "tool_calls": [], "retrieval_events": [], "metadata": {},
    })
    assert result.primary_category == "sql_failure"
    assert result.confidence_score >= 0.8


def test_prompt_regression_classification():
    clf = FailureClassifier()
    result = clf.classify({
        "task_type": "retrieval_qa", "prompt_version_id": "prompt_v5_regression_case",
        "overall_score": 0.5, "correctness_score": 0.3,
        "tool_calls": [], "retrieval_events": [{"relevance_score": 0.8}],
        "metadata": {"scenario": "prompt_regression"},
    })
    assert result.primary_category == "prompt_regression"


def test_unknown_low_confidence_flagged():
    clf = FailureClassifier()
    result = clf.classify({
        "task_type": "summarization", "overall_score": 0.75,
        "correctness_score": 0.8, "tool_calls": [], "retrieval_events": [],
        "metadata": {}, "_confidence_threshold": 0.6,
    })
    assert result.primary_category == "unknown"
    assert result.requires_human_review


def test_duplicate_pipeline_failure():
    clf = FailureClassifier()
    result = clf.classify({"is_duplicate": True})
    assert result.primary_category == "pipeline_failure"
