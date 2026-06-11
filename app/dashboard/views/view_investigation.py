import streamlit as st

from app.agent.graph import create_investigation_agent
from app.dashboard.components.layout import copilot_response, insight_card, page_header, warehouse_missing
from observatory.config.settings import get_settings

EXAMPLES = [
    "Why did reliability drop yesterday?",
    "Did prompt_v5_regression_case make things worse?",
    "Which model is safest for text to SQL?",
    "What are the top failure modes this week?",
    "Which runs need human review?",
    "Which agent is most expensive?",
]


def _ask(question: str, settings) -> None:
    if "copilot_msgs" not in st.session_state:
        st.session_state.copilot_msgs = []
    st.session_state.copilot_msgs.append({"role": "user", "text": question})
    agent = create_investigation_agent(settings)
    with st.spinner("Analyzing aggregated metrics..."):
        result = agent.investigate(question)
    st.session_state.copilot_msgs.append({"role": "assistant", "result": result})


def render() -> None:
    page_header(
        "Root Cause Copilot",
        "Ask plain English questions about reliability, prompt regressions, model performance, failures, cost, or latency.",
        "What should we investigate next?",
    )
    settings = get_settings()
    if not settings.resolve_path(settings.warehouse_path).exists():
        warehouse_missing()
        return

    insight_card(
        "How it works",
        "The copilot queries pre-aggregated reliability metrics — not raw logs. "
        "It never invents data. When LLM is disabled, you get deterministic metric summaries.",
    )

    if "copilot_msgs" not in st.session_state:
        st.session_state.copilot_msgs = []

    st.markdown("**Try an example question:**")
    cols = st.columns(3)
    for i, q in enumerate(EXAMPLES):
        with cols[i % 3]:
            if st.button(q, key=f"ex_{i}", use_container_width=True):
                _ask(q, settings)
                st.rerun()

    for msg in st.session_state.copilot_msgs:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["text"])
        else:
            with st.chat_message("assistant"):
                r = msg["result"]
                copilot_response(
                    summary=r.get("summary", ""),
                    evidence=r.get("evidence", ""),
                    action=r.get("recommended_action", ""),
                    llm_used=r.get("llm_used", False),
                    time_window=r.get("time_window_days"),
                    assumptions=r.get("assumptions"),
                    technical_error=r.get("error"),
                    metric_data=r.get("metric_data"),
                )

    q = st.chat_input("Ask about reliability, failures, prompts, or models...")
    if q:
        _ask(q, settings)
        st.rerun()
