-- Macro para extrair skills de texto
{% macro extract_skills(text_column, skills_list) %}
  CASE 
    {% for skill in skills_list %}
    WHEN LOWER({{ text_column }}) ~ '\b{{ skill.lower() }}\b' THEN TRUE
    {% endfor %}
    ELSE FALSE
  END
{% endmacro %}
