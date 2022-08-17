from collections import namedtuple

from sqlalchemy import MetaData, select, join

from django.utils.functional import cached_property

from db.records.operations import select as records_select
from db.columns.base import MathesarColumn
from db.columns.operations.select import get_column_name_from_attnum
from db.tables.operations.select import reflect_table_from_oid
from db.transforms.operations.apply import apply_transformations


class DBQuery:
    def __init__(
            self,
            base_table_oid,
            initial_columns,
            engine,
            transformations=None,
            name=None,
    ):
        self.base_table_oid = base_table_oid
        for initial_col in initial_columns:
            assert isinstance(initial_col, InitialColumn)
        self.initial_columns = initial_columns
        self.engine = engine
        self.transformations = transformations
        self.name = name

    # mirrors a method in db.records.operations.select
    def get_records(self, **kwargs):
        # NOTE how through this method you can perform a second batch of
        # transformations.  this reflects fact that we can form a query, and
        # then apply temporary transforms on it, like how you can apply
        # temporary transforms to a table when in a table view.
        return records_select.get_records(
            table=self.sa_relation,
            **kwargs,
        )

    # mirrors a method in db.records.operations.select
    def get_count(self, **kwargs):
        return records_select.get_count(table=self.sa_relation, **kwargs)

    @property
    def sa_output_columns(self):
        """
        Sequence of SQLAlchemy columns representing the output columns of the
        relation described by this query.
        """
        return tuple(
            MathesarColumn.from_column(sa_col, engine=self.engine)
            for sa_col
            in self.sa_relation.columns
        )

    @property
    def sa_relation(self):
        """
        A query describes a relation. This property is the result of parsing a
        query into a relation.
        """
        initial_relation = get_initial_relation(
            self.base_table_oid,
            self.initial_columns,
            self.engine,
        )
        transformations = self.transformations
        if transformations:
            transformed = apply_transformations(
                initial_relation,
                transformations,
            )
            return transformed
        else:
            return initial_relation


def get_initial_relation(
        base_oid,
        initial_columns,
        engine,
        metadata=None
):
    if metadata is None:
        metadata = MetaData()
    base_table = reflect_table_from_oid(base_oid, engine, metadata=metadata)
    from_clause = base_table
    jp_path_alias_map = {(): base_table}

    def _process_initial_column(col):
        nonlocal metadata
        nonlocal engine
        nonlocal from_clause
        nonlocal jp_path_alias_map
        col_name = get_column_name_from_attnum(col.reloid, col.attnum, engine)
        # Make the path hashable so it can be a dict key
        jp_path = _guarantee_jp_path_hashable(col.jp_path)

        if not jp_path:
            return base_table.columns[col_name]

        left_tab = base_table

        for i, jp in enumerate(jp_path):
            print("MAP: ", jp_path_alias_map)
            print(i, jp)
            left_tab = jp_path_alias_map[jp_path[:i]]
            print(left_tab.name)
            # left_tab = reflect_table_from_oid(
            #     jp[0][0], engine, metadata=metadata
            # ).alias()
            right_tab = reflect_table_from_oid(
                jp[1][0], engine, metadata=metadata
            ).alias()
            jp_path_alias_map[jp_path[:i+1]] = right_tab
            left_jcol = left_tab.columns[get_column_name_from_attnum(jp[0][0], jp[0][1], engine)]
            right_jcol = right_tab.columns[get_column_name_from_attnum(jp[1][0], jp[1][1], engine)]
            from_clause = from_clause.join(
                right_tab, onclause=left_jcol == right_jcol, isouter=True,
            )

        return right_tab.columns[col_name].label(col.alias)

    stmt = select(
        [_process_initial_column(col) for col in initial_columns]
    ).select_from(from_clause)
    return stmt.cte()


def _guarantee_jp_path_hashable(jp_path):
    if jp_path is not None:
        return tuple(
            [tuple([tuple(edge[0]), tuple(edge[1])]) for edge in jp_path]
        )

class InitialColumn:
    def __init__(
            self,
            reloid,
            attnum,
            alias,
            jp_path=None,
    ):
        # alias mustn't be an empty string
        assert isinstance(alias, str) and alias.strip() != ""
        self.reloid = reloid
        self.attnum = attnum
        self.alias = alias
        if jp_path is not None:
            self.jp_path = tuple(
                [tuple([ tuple(edge[0]), tuple(edge[1])]) for edge in jp_path]
            )
        else:
            self.jp_path = None

    @property
    def is_base_column(self):
        return self.jp_path is None


class JoinParams(
    namedtuple(
        'JoinParams',
        [
            'left_column',
            'right_column',
        ]
    )
):
    """
    Describes parameters for a join. Namely, the table and column pairs on both sides of the join.
    """
    def flip(self):
        return JoinParams(
            left_column=self.right_column,
            right_column=self.left_column,
        )

    @property
    def left_table(self):
        return self.left_column.table

    @property
    def right_table(self):
        return self.right_column.table


def _get_initial_relation(query):
    """
    The initial relation is the relation defined by the initial columns (`initial_columns`). It acts
    as input to the transformation pipeline (that's defined by `transformations`).
    """
#     sa_columns_to_select = []
#     from_clause = query.base_table
#     for initial_column in query.initial_columns:
#         from_clause, sa_column_to_select = _process_initial_column(
#             initial_column=initial_column,
#             from_clause=from_clause,
#         )
#         sa_columns_to_select.append(sa_column_to_select)
#     stmt = select(*sa_columns_to_select).select_from(from_clause)
#     return stmt.cte()


def _process_initial_column(initial_column, from_clause):
    if initial_column.is_base_column:
        col_to_select = initial_column.column
    else:
        from_clause, col_to_select = _nest_a_join(
            initial_column=initial_column,
            from_clause=from_clause,
        )
    # Give an alias/label to this column, since that's how it will be referenced in transforms.
    aliased_col_to_select = col_to_select.label(initial_column.alias)
    return from_clause, aliased_col_to_select


def _nest_a_join(from_clause, initial_column):
    jp_path = initial_column.jp_path
    target_sa_column = initial_column.column
    rightmost_table_alias = None
    ix_of_last_jp = len(jp_path) - 1
    for i, jp in enumerate(jp_path):
        is_last_jp = i == ix_of_last_jp
        # We want to alias the right-most table in the JP path, so that we can select from it later
        if is_last_jp:
            rightmost_table_alias = jp.right_table.alias()
            right_table = rightmost_table_alias
            right_column_reference = (
                # If we give the right table an alias, we have to use that alias whenever we
                # reference it
                _access_column_on_relation(
                    rightmost_table_alias,
                    jp.right_column,
                )
            )
        else:
            right_table = jp.right_table
            right_column_reference = jp.right_column
        left_table = from_clause
        left_column_reference = jp.left_column
        from_clause = join(
            left_table, right_table,
            left_column_reference == right_column_reference
        )
    # Here we produce the actual reference to the column we want to join in
    rightmost_table_target_column_reference = (
        _access_column_on_relation(
            rightmost_table_alias,
            target_sa_column,
        )
    )
    return from_clause, rightmost_table_target_column_reference


def _access_column_on_relation(relation, sa_column):
    column_name = sa_column.name
    return getattr(relation.c, column_name)
