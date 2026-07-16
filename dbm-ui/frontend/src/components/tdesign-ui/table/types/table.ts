import type {
  ErrorListObjectType,
  ScrollToElementParams,
  TableCol,
  TableErrorListMap,
  TableRowData,
  TableValidateTrigger,
} from 'tdesign-vue-next';
import type { PropType, Ref } from 'vue';

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
  fields?: { disabled?: boolean; field: string; label: string }[];
  /**
   * 字体大小
   */
  fontSize?: FontSizeEnum;
  /**
   * 是否显示全选
   */
  hasCheckAll?: boolean;
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

export const commonTableProps = {
  bkUiSettings: {
    type: Object as PropType<BkUiSettings>,
  },
  needCustomScroll: {
    default: true,
    type: Boolean,
  },
  onBkUiSettingsChange: {
    type: Function as PropType<(settings: { columns: string[]; fontSize: FontSizeEnum; rowSize: RowSizeEnum }) => void>,
  },
};

export type CommonTableProps = {
  bkUiSettings?: BkUiSettings;
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

export interface IRegisteredColumnProps extends TableCol {
  titleText: string;
}
