import type {
  EnhancedTableProps as TdEnhancedTableProps,
  PrimaryTableProps as TdPrimaryTableProps,
  TableRowData,
} from 'tdesign-vue-next/es/table';

import './theme/_index.less';

import EnhancedTable from './components/enhanced-table.vue';
import PrimaryTable from './components/primary-table.vue';
import TableColumn from './components/table-column.vue';
import type { CommonTableProps } from './types/table';

export type * from './types/table';
export { BaseTable } from 'tdesign-vue-next';
export type * from 'tdesign-vue-next/es/table';
export { EnhancedTable, PrimaryTable, TableColumn };
export const Table = PrimaryTable;
export type EnhancedTableProps<T extends TableRowData = TableRowData> = CommonTableProps & TdEnhancedTableProps<T>;
export type PrimaryTableProps<T extends TableRowData = TableRowData> = CommonTableProps & TdPrimaryTableProps<T>;
export type TableProps<T extends TableRowData = TableRowData> = CommonTableProps & TdPrimaryTableProps<T>;
