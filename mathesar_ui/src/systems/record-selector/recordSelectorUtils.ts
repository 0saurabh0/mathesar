import type { TableEntry } from '@mathesar/api/tables';
import type { Column } from '@mathesar/api/tables/columns';
import type { Result as ApiRecord } from '@mathesar/api/tables/records';

/**
 * - 'dataEntry' - each row is a button that submits the recordId via a Promise.
 * - 'navigation' - each row is a hyperlink to a Record Page.
 */
export type RecordSelectorPurpose = 'dataEntry' | 'navigation';

/** What kind of row are we in? */
export type CellLayoutRowType =
  | 'columnHeaderRow'
  | 'searchInputRow'
  | 'dividerRow'
  | 'dataRow';
/** What kind of column are we in? */
export type CellLayoutColumnType = 'dataColumn' | 'rowHeaderColumn';

export type CellState = 'focused' | 'acquiringFkValue';

export function getCellState({
  hasNestedSelectorOpen,
  hasFocus,
}: {
  hasNestedSelectorOpen: boolean;
  hasFocus: boolean;
}): CellState | undefined {
  if (hasNestedSelectorOpen) {
    return 'acquiringFkValue';
  }
  if (hasFocus) {
    return 'focused';
  }
  return undefined;
}

export function getPkValueInRecord(
  record: ApiRecord,
  columns: Column[],
): string | number {
  const pkColumn = columns.find((c) => c.primary_key);
  if (!pkColumn) {
    throw new Error('No primary key column found.');
  }
  const pkValue = record[pkColumn.id];
  if (!(typeof pkValue === 'string' || typeof pkValue === 'number')) {
    throw new Error('Primary key value is not a string or number.');
  }
  return pkValue;
}

export function getColumnIdToFocusInitially({
  table,
  columns,
}: {
  table: TableEntry | undefined;
  columns: Column[];
}): number | undefined {
  function getFromRecordSummaryTemplate() {
    if (!table) {
      return undefined;
    }
    const { template } = table.settings.preview_settings;
    const match = template.match(/\{\d+\}/)?.[0] ?? undefined;
    if (!match) {
      return undefined;
    }
    const id = parseInt(match.slice(1, -1), 10);
    if (Number.isNaN(id)) {
      return undefined;
    }
    return id;
  }

  function getFromColumns() {
    const column = columns.find((c) => !c.primary_key);
    if (!column) {
      return undefined;
    }
    return column.id;
  }

  return getFromRecordSummaryTemplate() ?? getFromColumns();
}
