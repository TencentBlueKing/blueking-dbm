import type { VxeTablePropTypes } from '@blueking/vxe-table';
export function createTableMerge(mergeCells: VxeTablePropTypes.MergeCells) {
  return ({ rowIndex, colIndex }: { rowIndex: number; colIndex: number }) => {
    // 找到起始单元格
    const startCell = mergeCells.find((cell) => cell.row === rowIndex && cell.col === colIndex);
    if (startCell) {
      return { rowspan: startCell.rowspan, colspan: startCell.colspan };
    }

    // 判断是否在覆盖范围内
    const isCovered = mergeCells.some((cell) => {
      const inRow = rowIndex >= cell.row && rowIndex < cell.row + cell.rowspan;
      const inCol = colIndex >= (cell.col as number) && colIndex < (cell.col as number) + cell.colspan;
      return inRow && inCol && !(rowIndex === cell.row && colIndex === cell.col);
    });

    if (isCovered) {
      return { rowspan: 0, colspan: 0 };
    }

    return {};
  };
}
