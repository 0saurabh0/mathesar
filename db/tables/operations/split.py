from sqlalchemy import exists, func, literal, select

from db import constants
from db.columns.base import MathesarColumn
from db.links.operations.create import create_foreign_key_link
from db.tables.operations.create import create_mathesar_table
from db.tables.operations.select import get_oid_from_table, reflect_table


def _split_column_list(columns_, extracted_column_names):
    extracted_columns = [
        col for col in columns_ if col.name in extracted_column_names
    ]
    remainder_columns = [
        col for col in columns_ if col.name not in extracted_column_names
    ]
    return extracted_columns, remainder_columns


def _create_split_tables(extracted_table_name, extracted_columns, remainder_table_name, schema, engine):
    extracted_table = create_mathesar_table(
        extracted_table_name,
        schema,
        extracted_columns,
        engine,
    )
    fk_column_name = f"{extracted_table.name}_{constants.ID}"
    remainder_table_oid = get_oid_from_table(remainder_table_name, schema, engine)
    extracted_table_oid = get_oid_from_table(extracted_table_name, schema, engine)
    create_foreign_key_link(engine, schema, fk_column_name, remainder_table_oid, extracted_table_oid)
    remainder_table_with_fk_key = reflect_table(remainder_table_name, schema, engine)
    return extracted_table, remainder_table_with_fk_key, fk_column_name


def _create_split_insert_stmt(old_table, extracted_table, extracted_columns, remainder_table, remainder_fk_name):
    SPLIT_ID = f"{constants.MATHESAR_PREFIX}_split_column_alias"
    extracted_column_names = [col.name for col in extracted_columns]
    split_cte = select(
        [
            old_table,
            func.dense_rank().over(order_by=extracted_columns).label(SPLIT_ID)
        ]
    ).cte()
    cte_extraction_columns = (
        [split_cte.columns[SPLIT_ID]]
        + [split_cte.columns[n] for n in extracted_column_names]
    )
    extract_sel = select(
        cte_extraction_columns,
        distinct=True
    )
    extract_ins_cte = (
        extracted_table
        .insert()
        .from_select([constants.ID] + extracted_column_names, extract_sel)
        .returning(literal(1))
        .cte()
    )
    fk_update_dict = {remainder_fk_name: split_cte.c[SPLIT_ID]}
    split_ins = (
        remainder_table
        .update().
        values(**fk_update_dict).
        where(remainder_table.c[constants.ID] == split_cte.c[constants.ID],
              exists(extract_ins_cte.select()))
    )
    return split_ins


def extract_columns_from_table(old_table_name, extracted_column_names, extracted_table_name, remainder_table_name, schema, engine, drop_original_table=False):
    old_table = reflect_table(old_table_name, schema, engine)
    old_columns = (MathesarColumn.from_column(col) for col in old_table.columns)
    old_non_default_columns = [
        col for col in old_columns if not col.is_default
    ]
    extracted_columns, remainder_columns = _split_column_list(
        old_non_default_columns, extracted_column_names,
    )
    with engine.begin() as conn:
        extracted_table, remainder_table_with_fk_column, fk_column_name = _create_split_tables(
            extracted_table_name,
            extracted_columns,
            remainder_table_name,
            schema,
            engine,
        )
        split_ins = _create_split_insert_stmt(
            old_table,
            extracted_table,
            extracted_columns,
            old_table,
            fk_column_name,
        )
        conn.execute(split_ins)
    if drop_original_table:
        old_table.drop()

    return extracted_table, remainder_table_with_fk_column, fk_column_name
