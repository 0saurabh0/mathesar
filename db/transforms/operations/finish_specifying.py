from db.tables.operations import select as tables_select
from db.tables.operations.select import get_joinable_tables
from db.transforms.base import Summarize, SelectSubsetOfColumns
from db.columns.operations.select import get_column_from_oid_and_attnum


def finish_specifying_summarize_transform(
    db_query, ix_of_summarize_transform, engine, metadata
):
    """
    Adds missing input aliases to the summarize transform.

    Will find input aliases that are not mentioned in the summarize_transform and will add each
    of them to its group-by list and/or aggregate-on list.

    If the user selected input alias (summarize's base grouping column) is not unique-constrained,
    will put the unmentioned input aliases in the aggregation list.

    If the user selected input alias (summarize's base grouping column) is unique-constrained,
    then it might put at least some input aliases in the grouping list, depending on what
    _should_group_by returns.
    """
    summarize_transform = db_query.transformations[ix_of_summarize_transform]
    assert type(summarize_transform) is Summarize
    aliases_to_be_added_to_group_by, aliases_to_be_added_to_agg_on = \
        _split_missing_input_aliases_into_group_and_agg_lists(
            db_query, ix_of_summarize_transform, engine, metadata
        )
    if aliases_to_be_added_to_group_by:
        summarize_transform = \
            summarize_transform.get_new_with_aliases_added_to_group_by(
                aliases_to_be_added_to_group_by
            )
    if aliases_to_be_added_to_agg_on:
        summarize_transform = \
            summarize_transform.get_new_with_aliases_added_to_agg_on(
                aliases_to_be_added_to_agg_on
            )
    return summarize_transform


def _split_missing_input_aliases_into_group_and_agg_lists(
    db_query, ix_of_summarize_transform, engine, metadata,
):
    aliases_to_be_added_to_group_by = []
    aliases_to_be_added_to_agg_on = []
    summarize_transform = db_query.transformations[ix_of_summarize_transform]
    missing_input_aliases = \
        _get_missing_input_aliases(db_query, summarize_transform)
    if not missing_input_aliases:
        # If all input aliases for summarize transform are in the transform's group-by or
        # aggregate-on lists, there's nothing to do.
        return aliases_to_be_added_to_group_by, aliases_to_be_added_to_agg_on
    # A summarize transform has a base_grouping_column (which is an alias) around
    # which our suggestions will be based.
    base_grouping_alias = summarize_transform.base_grouping_column
    base_grouping_initial_column = \
        _get_initial_column_by_alias(
            db_query, base_grouping_alias
        )
    # We'll always want base_grouping_column in the "group-by list";
    if base_grouping_alias in missing_input_aliases:
        aliases_to_be_added_to_group_by.append(base_grouping_alias)
        missing_input_aliases.remove(base_grouping_alias)
    # Most of logic in the rest of method is around whether or not we can add some of the other
    # missing input aliases to the "group-by list"; otherwise we'll put them in "aggregate-on list".
    can_add_other_aliases_to_group_by = (
        base_grouping_initial_column is not None
        and _is_initial_column_unique_constrained(
            base_grouping_initial_column, engine, metadata
        )
    )
    if can_add_other_aliases_to_group_by:
        oids_of_joinable_tables_with_single_results = \
            _get_oids_of_joinable_tables_with_single_results(
                db_query, engine, metadata
            )
        oid_of_base_grouping_initial_column = \
            _get_oid_of_initial_column(base_grouping_initial_column)
        for input_alias in missing_input_aliases:
            initial_column = _get_initial_column_by_alias(db_query, input_alias)
            if _should_group_by(
                _get_oid_of_initial_column(initial_column),
                oid_of_base_grouping_initial_column,
                oids_of_joinable_tables_with_single_results,
            ):
                alias_list_to_add_to = aliases_to_be_added_to_group_by
            else:
                alias_list_to_add_to = aliases_to_be_added_to_agg_on
            alias_list_to_add_to.append(initial_column.alias)
    else:
        aliases_to_be_added_to_agg_on = list(missing_input_aliases)
    return aliases_to_be_added_to_group_by, aliases_to_be_added_to_agg_on


def _get_initial_column_by_alias(db_query, alias):
    # IDEA i can make guesses about how each transform changes input alias list
    # most don't; that can be portrayed in a mapping, if it carries over, then input_alias -> input_alias,
    # if it changes, input_alias -> output_alias, if it gets removed input_alias -> None
    # TODO
    for initial_column in initial_columns:
        if initial_column.alias == alias:
            return initial_column


def _get_missing_input_aliases(db_query, ix_of_summarize_transform):
    """
    # TODO explain missing
    """
    summarize_transform = db_query.transformations[ix_of_summarize_transform]
    group_by_aliases = summarize_transform.grouping_input_aliases
    agg_on_aliases = summarize_transform.aggregation_input_aliases
    aliases_in_summarize = group_by_aliases + agg_on_aliases
    input_aliases = _get_input_aliases(db_query, ix_of_summarize_transform)
    return [
        input_alias
        for input_alias
        in input_aliases
        if input_alias not in aliases_in_summarize
    ]


def _get_input_aliases(db_query, ix_of_summarize_transform):
    # TODO
    pass


def _get_initial_columns_not_in_summarize(db_query, summarize_transform):
    initial_columns = db_query.initial_columns
    group_by_aliases = summarize_transform.grouping_input_aliases
    agg_on_aliases = summarize_transform.aggregation_input_aliases
    aliases_in_summarize = group_by_aliases + agg_on_aliases
    return [
        initial_column
        for initial_column in
        initial_columns
        if initial_column.alias not in aliases_in_summarize
    ]


def _should_group_by(
    oid_of_initial_column,
    oid_of_base_grouping_group_by_col,
    oids_of_joinable_tables_with_single_results,
):
    """
    For the sake of efficiency, we're not checking here that base_grouping_group_by_col is unique
    constrained: it is presumed that that is the case.
    """
    is_on_table_of_base_grouping_column = \
        oid_of_initial_column == oid_of_base_grouping_group_by_col
    is_single_result = \
        oid_of_initial_column in oids_of_joinable_tables_with_single_results
    should_group_by = \
        is_on_table_of_base_grouping_column or is_single_result
    return should_group_by


def _get_oids_of_joinable_tables_with_single_results(
    db_query, engine, metadata,
):
    joinable_tables = \
        get_joinable_tables(engine, metadata, db_query.base_table_oid)
    return set(
        _get_oid_of_joinable_table(joinable_table)
        for joinable_table
        in joinable_tables
        if _has_single_result(joinable_table)
    )


def _is_initial_column_unique_constrained(initial_column, engine, metadata):
    oid = _get_oid_of_initial_column(initial_column)
    attnum = initial_column.attnum
    sa_column = get_column_from_oid_and_attnum(
        table_oid=oid,
        attnum=attnum,
        engine=engine,
        metadata=metadata,
    )
    return _is_sa_column_unique_constrained(sa_column)


def _is_sa_column_unique_constrained(sa_column):
    return sa_column.primary_key or sa_column.unique


def _get_oid_of_initial_column(initial_column):
    return initial_column.reloid


def _get_oid_of_joinable_table(joinable_table):
    joinable_table_oid = joinable_table[tables_select.TARGET]
    return joinable_table_oid


def _has_single_result(joinable_table):
    has_multiple_results = joinable_table[tables_select.MULTIPLE_RESULTS]
    assert type(has_multiple_results) is bool
    return not has_multiple_results
