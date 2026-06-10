from observatory.data_generation.synthetic_run_generator import FailureRates, SyntheticRunGenerator


def test_generator_produces_expected_volume():
    gen = SyntheticRunGenerator(seed=42)
    batch = gen.generate_batch(1000)
    total = len(batch.agent_runs) + len(batch.malformed_records)
    assert total == 1000


def test_failure_rate_distribution_approximate():
    gen = SyntheticRunGenerator(seed=42)
    batch = gen.generate_batch(5000)
    counts = batch.scenario_counts
    assert counts.get("success", 0) > 2000  # ~60%
    assert counts.get("malformed_record", 0) > 50   # ~2%
    assert counts.get("duplicate_run_id", 0) > 20   # ~1%


def test_required_agents_and_models_present():
    gen = SyntheticRunGenerator(seed=1)
    batch = gen.generate_batch(500)
    agents = {r["agent_name"] for r in batch.agent_runs}
    models = {r["model_name"] for r in batch.agent_runs}
    prompts = {r["prompt_version_id"] for r in batch.agent_runs}
    for a in ["sql_analyst_agent", "research_assistant_agent", "tool_router_agent"]:
        assert a in agents
    for m in ["gpt_4o_mini_simulated", "claude_sonnet_simulated"]:
        assert m in models
    assert "prompt_v5_regression_case" in prompts


def test_failure_rates_normalize():
    rates = FailureRates(success=0.6, sql_syntax=0.06).normalize()
    total = sum(w for _, w in rates.choices())
    assert abs(total - 1.0) < 0.001
