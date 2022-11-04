from db.types.base import PostgresType


def test_columns(client, minimal_patents_query):
    ui_query = minimal_patents_query
    base_table_name = ui_query.base_table.name
    response = client.get(f'/api/db/v0/queries/{ui_query.id}/columns/')
    response_json = response.json()
    assert response.status_code == 200
    assert response_json == [
        {
            'alias': 'col1',
            'display_name': 'Column 1',
            'type': PostgresType.TEXT.id,
            'type_options': None,
            'display_options': dict(a=1),
            'is_initial_column': True,
            'base_column_name': 'Center',
            'base_table_name': base_table_name,
        },
        {
            'alias': 'col2',
            'display_name': 'Column 2',
            'type': PostgresType.TEXT.id,
            'type_options': None,
            'display_options': dict(b=2),
            'is_initial_column': True,
            'base_column_name': 'Case Number',
            'base_table_name': base_table_name,
        },
    ]
