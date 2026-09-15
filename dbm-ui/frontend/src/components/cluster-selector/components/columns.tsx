import type { PrimaryTableCol } from 'tdesign-vue-next';

/**
 * 兼容外部以 bkui Table 格式传入的自定义列（field/label/render/showOverflowTooltip）
 */
export const transBkuiColumns = (columns: Record<string, any>[]): PrimaryTableCol[] =>
  columns.map((item) => {
    const { field, label, render, showOverflow, showOverflowTooltip, ...rest } = item;
    return {
      ...rest,
      cell: render ? (_, { row }: { row: any }) => render({ cell: row[field], data: row, row }) : undefined,
      colKey: field,
      ellipsis: showOverflow || showOverflowTooltip ? true : undefined,
      title: label,
    };
  });

// TODO: 后续选择器的其他公共列也抽取到这里来
