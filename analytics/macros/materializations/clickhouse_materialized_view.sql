{% materialization clickhouse_materialized_view, adapter='clickhouse' %}

  {%- set target_relation = api.Relation.create(
      identifier=this.identifier,
      schema=this.schema,
      database=this.database,
      type='table'
  ) -%}

  {%- set materialization_schema = config.require('materialization_s') -%}
  {%- set materialization_identifier = config.require('materialization_i') -%}

  {{ log("This identifier: " ~ this.materialization_identifier, info=True) }}
  {{ log("This schema: " ~ this.materialization_schema, info=True) }}
  

  {%- set materialization_table = api.Relation.create(
      database=materialization_schema,
      schema=materialization_schema,
      identifier=materialization_identifier,
      type='table'
  ) -%}
  
  {{ run_hooks(pre_hooks) }}

  {%- set ddl -%}
    CREATE MATERIALIZED VIEW IF NOT EXISTS {{ target_relation }}
    TO {{ materialization_table }}
    AS {{ sql }}
  {%- endset -%}

  {{ log("Creating materialized view with DDL:", info=True) }}
  {{ log(ddl, info=True) }}

  {% call statement('main') -%}
    {{ ddl }}
  {%- endcall %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}