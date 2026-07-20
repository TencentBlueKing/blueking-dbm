import type {
  ErrorListObjectType,
  ScrollToElementParams,
  TableCol,
  TableErrorListMap,
  TableRowData,
  TableValidateTrigger,
} from 'tdesign-vue-next';
import type { PropType, Ref } from 'vue';

export type BkUiTableCol = {
  /**
   * 未进入用户配置的新列是否默认显示
   */
  defaultChecked?: boolean;
} & TableCol;

export interface BkUiSettingsField {
  defaultChecked?: boolean;
  disabled?: boolean;
  field: string;
  label: string;
}

/**
 * 蓝鲸table 列配置 如果配置为空对象，组件内部流转状态
 */
export type BkUiSettings = {
  /**
   * 选中列 不配置（undefined）则默认全选
   */
  checked?: string[];
  /**
   * 禁用列 配置了 disabled 则禁用并选中
   */
  disabled?: string[];
  /**
   * 自定义列配置
   * 配置了 disabled 则禁用并选中
   */
  fields?: BkUiSettingsField[];
  /**
   * 字体大小
   */
  fontSize?: FontSizeEnum;
  /**
   * 是否显示全选
   */
  hasCheckAll?: boolean;
  /**
   * 所有可配置列的显示顺序
   */
  order?: string[];
  /**
   * 行高
   */
  rowSize?: RowSizeEnum;
};

export const FontSize = {
  large: 14,
  medium: 12,
} as const;
export const RowSize = {
  large: 56,
  medium: 42,
  mini: 36,
  small: 32,
} as const;

export type FontSizeEnum = keyof typeof FontSize;
export type RowSizeEnum = keyof typeof RowSize;

export interface BkUiSettingsChangePayload {
  columns: string[];
  fontSize: FontSizeEnum;
  order: string[];
  rowSize: RowSizeEnum;
}

export const commonTableProps = {
  bkUiSettings: {
    type: Object as PropType<BkUiSettings>,
  },
  columns: {
    type: Array as PropType<BkUiTableCol[]>,
  },
  needCustomScroll: {
    default: true,
    type: Boolean,
  },
  onBkUiSettingsChange: {
    type: Function as PropType<(settings: BkUiSettingsChangePayload) => void>,
  },
};

export type CommonTableProps = {
  bkUiSettings?: BkUiSettings;
  columns?: BkUiTableCol[];
};

export type EnhancedTableRefExpose = {
  primaryTableRef: Ref<PrimaryTableRefExpose>;
} & Pick<
  PrimaryTableRefExpose,
  'clearValidateData' | 'refreshTable' | 'scrollToElement' | 'validateRowData' | 'validateTableData'
>;

export type PrimaryTableRefExpose = {
  clearValidateData: () => void;
  refreshTable: () => void;
  scrollColumnIntoView: (colKey: string) => void;
  scrollToElement: (data: ScrollToElementParams) => void;
  validateRowData: (
    rowValue: any,
  ) => Promise<{ result: ErrorListObjectType<TableRowData>[]; trigger: TableValidateTrigger }>;
  validateTableCellData: () => Promise<{ result: TableErrorListMap }>;
  validateTableData: () => Promise<{ result: TableErrorListMap }>;
};

export type IRegisteredColumnProps = {
  titleText: string;
} & BkUiTableCol;
