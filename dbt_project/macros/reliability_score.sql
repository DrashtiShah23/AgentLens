{% macro reliability_score(overall_score_column) %}
    coalesce({{ overall_score_column }}, 0)
{% endmacro %}
