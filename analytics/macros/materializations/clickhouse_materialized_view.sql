{% materialization clickhouse_materialized_view, adapter='clickhouse' %}

  {%- set target_relation = api.Relation.create(
      identifier=this.identifier,
      schema=this.schema,
      database=this.database,
      type='table'
  ) -%}

  {%- set materialization_schema = config.require('materialization_schema') -%}
  {%- set materialization_identifier = config.require('materialization_identifier') -%}
  {%- set order_by = config.require('order_by') -%}

  {{ log("Materialization identifier: " ~ materialization_identifier, info=True) }}
  {{ log("Materialization schema: " ~ materialization_schema, info=True) }}
  

  {%- set materialization_table = api.Relation.create(
      database=materialization_schema,
      schema=materialization_schema,
      identifier=materialization_identifier,
      type='table'
  ) -%}
  
  {{ run_hooks(pre_hooks) }}

  {%- set compiled_sql = render(sql) -%}

  {%- set ddl -%}
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ target_relation }}
    TO {{ materialization_table }}
    AS {{ compiled_sql }}
  {%- endset -%}

  {{ log("Creating materialized view with DDL:", info=True) }}
  {{ log(ddl, info=True) }}

  {% call statement('main') -%}
    {{ ddl }}
  {%- endcall %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}