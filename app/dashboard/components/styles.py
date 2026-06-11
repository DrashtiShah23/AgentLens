"""Dark theme design system for AI Failure Observatory."""

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp { background-color: #0b1220; }
    .block-container { padding-top: 1.25rem; max-width: 1380px; }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #e2e8f0;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        border-right: 1px solid #1e293b;
    }
    div[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    div[data-testid="stSidebar"] .stRadio label { font-weight: 500; font-size: 0.92rem; }

    h1, h2, h3, h4 { color: #f1f5f9 !important; }
    p, span, label { color: #cbd5e1; }
    .stMetric label { color: #94a3b8 !important; }
    .stMetric [data-testid="stMetricValue"] { color: #f8fafc !important; }

    .obs-hero {
        background: linear-gradient(135deg, #111827 0%, #1e1b4b 45%, #0f172a 100%);
        border: 1px solid #312e81;
        border-radius: 16px;
        padding: 2rem 2.25rem;
        margin-bottom: 1.25rem;
    }
    .obs-hero h1 { font-size: 1.85rem; font-weight: 700; color: #f8fafc !important; margin: 0 0 0.4rem 0; }
    .obs-hero .subtitle { font-size: 1.05rem; color: #a5b4fc; margin: 0 0 0.6rem 0; }
    .obs-hero .desc { font-size: 0.9rem; color: #94a3b8; line-height: 1.55; margin: 0; }
    .obs-hero .purpose { font-size: 0.82rem; color: #64748b; margin-top: 0.75rem; font-style: italic; }

    .obs-page-title { font-size: 1.5rem; font-weight: 700; color: #f8fafc !important; margin-bottom: 0.25rem; }
    .obs-page-subtitle { font-size: 0.95rem; color: #94a3b8; margin-bottom: 1rem; line-height: 1.5; }

    .obs-section {
        font-size: 1rem; font-weight: 600; color: #e2e8f0 !important;
        margin: 1.25rem 0 0.65rem 0; padding-bottom: 0.4rem;
        border-bottom: 1px solid #1e293b;
    }

    .obs-metric {
        background: #111827; border: 1px solid #1e293b; border-radius: 12px;
        padding: 0.9rem 1rem; min-height: 118px;
    }
    .obs-metric.healthy { border-top: 3px solid #22c55e; }
    .obs-metric.warning { border-top: 3px solid #eab308; }
    .obs-metric.critical { border-top: 3px solid #ef4444; }
    .obs-metric.neutral { border-top: 3px solid #64748b; }
    .obs-metric.prompt { border-top: 3px solid #a855f7; }
    .obs-metric.model { border-top: 3px solid #3b82f6; }
    .obs-metric.cost { border-top: 3px solid #f97316; }

    .obs-metric-icon { font-size: 1.1rem; margin-bottom: 0.2rem; }
    .obs-metric-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: #94a3b8; }
    .obs-metric-value { font-size: 1.55rem; font-weight: 700; color: #f8fafc; margin: 0.2rem 0; }
    .obs-metric-interp { font-size: 0.72rem; color: #64748b; line-height: 1.35; margin-top: 0.3rem; }

    .obs-badge {
        display: inline-block; padding: 0.25rem 0.65rem; border-radius: 6px;
        font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
        border: 1px solid transparent;
    }
    .obs-badge-healthy { background: #166534; color: #bbf7d0; border-color: #22c55e; }
    .obs-badge-warning { background: #854d0e; color: #fef08a; border-color: #eab308; }
    .obs-badge-critical { background: #991b1b; color: #fecaca; border-color: #ef4444; }
    .obs-badge-info { background: #1d4ed8; color: #dbeafe; border-color: #3b82f6; }
    .obs-badge-regression { background: #6b21a8; color: #f3e8ff; border-color: #a855f7; }
    .obs-badge-prompt { background: #5b21b6; color: #ede9fe; border-color: #8b5cf6; }
    .obs-badge-model { background: #1e40af; color: #dbeafe; border-color: #3b82f6; }

    .obs-health-banner {
        border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem;
        font-size: 1rem; font-weight: 600;
    }
    .obs-health-banner.healthy { background: #14532d; color: #bbf7d0; border: 1px solid #22c55e; }
    .obs-health-banner.warning { background: #713f12; color: #fef08a; border: 1px solid #eab308; }
    .obs-health-banner.critical { background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; }

    .obs-risk-card {
        background: #1c1917; border: 1px solid #ea580c; border-left: 4px solid #f97316;
        border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 0.85rem;
        color: #fed7aa; font-size: 0.9rem;
    }
    .obs-risk-card strong { color: #fdba74; }

    div[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] label[data-baseweb="radio"] {
        background: #1e293b; border: 1px solid #334155; border-radius: 8px;
        padding: 0.45rem 0.65rem; margin-bottom: 0.35rem;
    }
    div[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
        background: #312e81; border-color: #6366f1; color: #e0e7ff !important;
    }

    .obs-insight {
        background: #0f172a; border: 1px solid #1e3a5f; border-left: 4px solid #3b82f6;
        border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 0.85rem;
        font-size: 0.88rem; color: #cbd5e1; line-height: 1.5;
    }
    .obs-insight strong { color: #93c5fd; }

    .obs-action {
        background: #052e16; border: 1px solid #166534; border-left: 4px solid #22c55e;
        border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 0.85rem;
        font-size: 0.88rem; color: #bbf7d0; line-height: 1.5;
    }
    .obs-action strong { color: #4ade80; }

    .obs-alert {
        background: #450a0a; border: 1px solid #991b1b; border-left: 4px solid #ef4444;
        border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 0.85rem;
        color: #fecaca; font-size: 0.88rem;
    }

    .obs-card {
        background: #111827; border: 1px solid #1e293b; border-radius: 12px;
        padding: 1rem 1.15rem; margin-bottom: 0.75rem;
    }
    .obs-card-title { font-weight: 600; color: #f1f5f9; font-size: 0.95rem; }
    .obs-card-body { color: #94a3b8; font-size: 0.82rem; margin-top: 0.35rem; line-height: 1.45; }

    .obs-empty {
        background: #111827; border: 1px dashed #334155; border-radius: 12px;
        padding: 2rem; text-align: center; color: #94a3b8;
    }
    .obs-empty-title { font-weight: 600; color: #e2e8f0; margin-bottom: 0.4rem; }

    .obs-scorecard {
        background: linear-gradient(145deg, #111827, #1e1b4b);
        border: 1px solid #312e81; border-radius: 14px; padding: 1.1rem 1.25rem;
    }
    .obs-scorecard-rank { font-size: 1.4rem; font-weight: 800; color: #a5b4fc; }
    .obs-scorecard-name { font-size: 1rem; font-weight: 600; color: #f8fafc; }
    .obs-scorecard-stat { font-size: 0.8rem; color: #94a3b8; margin-top: 0.3rem; }

    .obs-response {
        background: #111827; border: 1px solid #1e293b; border-radius: 14px;
        padding: 1.25rem; margin: 0.75rem 0;
    }
    .obs-response-label {
        font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
        color: #64748b; letter-spacing: 0.05em; margin-bottom: 0.3rem;
    }
    .obs-response-text { color: #e2e8f0; font-size: 0.92rem; line-height: 1.5; margin-bottom: 0.9rem; }

    .obs-demo { background: #052e16; border: 1px solid #166534; border-radius: 8px;
        padding: 0.55rem 0.9rem; font-size: 0.78rem; color: #86efac; margin-bottom: 0.85rem; }

    [data-testid="stDataFrame"] { border: 1px solid #1e293b; border-radius: 8px; }
</style>
"""

CHART_COLORS = {
    "healthy": "#22c55e",
    "warning": "#eab308",
    "critical": "#ef4444",
    "prompt": "#a855f7",
    "model": "#3b82f6",
    "cost": "#f97316",
    "latency": "#fb923c",
    "neutral": "#64748b",
    "palette": ["#22c55e", "#3b82f6", "#a855f7", "#f97316", "#ef4444", "#14b8a6", "#eab308", "#ec4899"],
    "severity": {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#22c55e"},
    "failure": {
        "hallucination": "#ec4899", "sql_failure": "#ef4444", "retrieval_failure": "#3b82f6",
        "tool_failure": "#f97316", "prompt_regression": "#a855f7", "format_failure": "#eab308",
        "latency_failure": "#fb923c", "cost_failure": "#f59e0b", "reasoning_failure": "#8b5cf6",
        "pipeline_failure": "#64748b", "unknown": "#94a3b8",
    },
}

FAILURE_COLORS = CHART_COLORS["failure"]

PLOTLY_LAYOUT = {
    "font": {"family": "Inter, sans-serif", "size": 12, "color": "#94a3b8"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "#111827",
    "margin": {"l": 48, "r": 24, "t": 52, "b": 44},
    "hovermode": "closest",
    "legend": {"bgcolor": "rgba(17,24,39,0.8)", "font": {"color": "#cbd5e1"}},
}

PLOTLY_AXIS = {"gridcolor": "#1e293b", "linecolor": "#334155", "zerolinecolor": "#334155"}

FAILURE_LABELS = {
    "hallucination": "Unsupported Answer",
    "retrieval_failure": "Missing Context",
    "tool_failure": "Tool Error",
    "sql_failure": "SQL Generation Error",
    "prompt_regression": "Prompt Regression",
    "reasoning_failure": "Reasoning Error",
    "format_failure": "Output Format Error",
    "latency_failure": "Slow Response",
    "cost_failure": "Cost Spike",
    "pipeline_failure": "Pipeline Issue",
    "unknown": "Unknown Issue",
}

SEVERITY_LABELS = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

TASK_LABELS = {
    "text_to_sql": "Text to SQL",
    "retrieval_qa": "Context QA",
    "tool_use": "Tool Use",
    "summarization": "Summarization",
    "classification": "Classification",
}
