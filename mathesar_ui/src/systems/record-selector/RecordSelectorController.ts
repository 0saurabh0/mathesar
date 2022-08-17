import { getContext, setContext } from 'svelte';
import type { Readable } from 'svelte/store';
import { derived, get, writable } from 'svelte/store';

import type { Column } from '@mathesar/api/tables/columns';
import type { DBObjectEntry } from '@mathesar/AppTypes';
import { currentDbAbstractTypes } from '@mathesar/stores/abstract-types';
import { Meta } from '@mathesar/stores/table-data';
import { TabularData } from '@mathesar/stores/table-data/tabularData';
import Pagination from '@mathesar/utils/Pagination';

interface RecordSelectorControllerProps {
  onOpen?: () => void;
  onClose?: () => void;
}

type FkCellValue = string | number;

export class RecordSelectorController {
  private onOpen: () => void;

  private onClose: () => void;

  isOpen = writable(false);

  submit: (v: FkCellValue) => void = () => {};

  cancel: () => void = () => {};

  tableId = writable<DBObjectEntry['id'] | undefined>(undefined);

  tabularData: Readable<TabularData | undefined>;

  columnWithNestedSelectorOpen = writable<Column | undefined>(undefined);

  constructor(props: RecordSelectorControllerProps = {}) {
    this.onOpen = props.onOpen ?? (() => {});
    this.onClose = props.onClose ?? (() => {});

    this.tabularData = derived(this.tableId, (tableId) => {
      if (!tableId) {
        return undefined;
      }
      return new TabularData({
        id: tableId,
        abstractTypesMap: get(currentDbAbstractTypes).data,
        meta: new Meta({ pagination: new Pagination({ size: 10 }) }),
      });
    });
  }

  private open(): void {
    const tabularData = get(this.tabularData);
    if (tabularData) {
      tabularData.meta.searchFuzzy.update((s) => s.drained());
    }
    this.isOpen.set(true);
    this.onOpen();
  }

  private close(): void {
    this.submit = () => {};
    this.cancel = () => {};
    this.isOpen.set(false);
    this.onClose();
  }

  acquireUserInput({
    tableId,
  }: {
    tableId: DBObjectEntry['id'];
  }): Promise<FkCellValue | undefined> {
    this.tableId.set(tableId);
    this.open();
    return new Promise((resolve) => {
      this.submit = (v) => {
        resolve(v);
        this.close();
      };
      this.cancel = () => {
        resolve(undefined);
        this.close();
      };
    });
  }
}

const contextKey = {};

export function setNewRecordSelectorControllerInContext(
  props: RecordSelectorControllerProps = {},
): RecordSelectorController {
  const recordSelectorController = new RecordSelectorController(props);
  setContext(contextKey, recordSelectorController);
  return recordSelectorController;
}

export function getRecordSelectorFromContext(): RecordSelectorController {
  return getContext(contextKey);
}
