{% macro safe_divide(numerator, denominator, default_value=0) %}
    case
        when {{ denominator }} is null or {{ denominator }} = 0 then {{ default_value }}
        else {{ numerator }} / {{ denominator }}
    end
{% endmacro %}
