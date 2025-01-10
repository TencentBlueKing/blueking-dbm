import _ from 'lodash';
import { onBeforeUnmount, onMounted, type Ref, ref, watch } from 'vue';

import type { IContext as IColumnContext } from '../Column.vue';

export default function (
  tableRef: Ref<HTMLElement | undefined>,
  tableColumnResizeRef: Ref<HTMLElement | undefined>,
  columnList: Ref<IColumnContext[]>,
) {
  let dragable = false;

  const columnSizeConfig = ref<
    Record<
      string,
      {
        width?: number;
        minWidth?: number;
        maxWidth?: number;
        renderWidth: number;
      }
    >
  >({});

  const dragging = ref(false);
  const dragState = ref({
    startMouseLeft: 0,
    startLeft: 0,
    startColumnLeft: 0,
    tableLeft: 0,
  });

  watch(
    columnList,
    () => {
      if (!tableRef.value) {
        return;
      }
      const tableWidth = tableRef.value.getBoundingClientRect().width;

      const columnSizeConfigCache = { ...columnSizeConfig.value };

      const maxColumn: IColumnContext[] = [];
      const minColumn: IColumnContext[] = [];
      const pxColumn: IColumnContext[] = [];
      const autoColumn: IColumnContext[] = [];

      columnList.value.forEach((column) => {
        if (column.props.width) {
          pxColumn.push(column);
        } else if (column.props.minWidth) {
          minColumn.push(column);
        } else if (column.props.maxWidth) {
          maxColumn.push(column);
        } else {
          autoColumn.push(column);
        }
      });

      let totalWidth = 0;
      pxColumn.forEach((column) => {
        if (columnSizeConfigCache[column.key]) {
          totalWidth += columnSizeConfigCache[column.key].renderWidth;
          return;
        }
        columnSizeConfigCache[column.key] = {
          width: column.props.width,
          renderWidth: Number(column.props.width),
        };
        totalWidth += Number(column.props.width);
      });
      minColumn.forEach((column) => {
        if (columnSizeConfigCache[column.key]) {
          totalWidth += columnSizeConfigCache[column.key].renderWidth;
          return;
        }
        columnSizeConfigCache[column.key] = {
          minWidth: column.props.minWidth,
          renderWidth: Number(column.props.minWidth),
        };
        totalWidth += Number(column.props.minWidth);
      });

      const remainWidth = tableWidth - totalWidth;

      let meanWidth =
        remainWidth > 0 ? Math.floor(remainWidth / (minColumn.length + maxColumn.length + autoColumn.length)) : 0;

      let extraWidth = 0;
      maxColumn.forEach((column) => {
        if (columnSizeConfigCache[column.key]) {
          return;
        }
        let renderWidth = meanWidth;
        if (Number(column.props.maxWidth) <= meanWidth) {
          renderWidth = Number(column.props.maxWidth);
          extraWidth += meanWidth - Number(column.props.maxWidth);
        }
        columnSizeConfigCache[column.key] = {
          maxWidth: column.props.maxWidth,
          renderWidth,
        };
      });
      meanWidth += Math.floor(extraWidth / (autoColumn.length + minColumn.length));
      minColumn.forEach((column) => {
        Object.assign(columnSizeConfigCache[column.key], {
          renderWidth: columnSizeConfigCache[column.key].renderWidth + meanWidth,
        });
      });
      autoColumn.forEach((column) => {
        columnSizeConfigCache[column.key] = {
          renderWidth: meanWidth,
        };
      });

      const renderColumnWidthTotal = Object.values(columnSizeConfigCache).reduce(
        (result, item) => result + item.renderWidth,
        0,
      );
      if (renderColumnWidthTotal < tableWidth) {
        const fixWidth = tableWidth - renderColumnWidthTotal;
        if (minColumn.length > 0) {
          columnSizeConfigCache[minColumn[0].key].renderWidth =
            columnSizeConfigCache[minColumn[0].key].renderWidth + fixWidth;
        } else if (autoColumn.length > 0) {
          columnSizeConfigCache[autoColumn[0].key].renderWidth =
            columnSizeConfigCache[autoColumn[0].key].renderWidth + fixWidth;
        } else if (maxColumn.length > 0) {
          columnSizeConfigCache[maxColumn[0].key].renderWidth =
            columnSizeConfigCache[maxColumn[0].key].renderWidth + fixWidth;
        }
      }

      columnSizeConfig.value = columnSizeConfigCache;
    },
    {
      immediate: true,
    },
  );

  const handleMouseDown = (event: MouseEvent) => {
    if (!dragable) {
      return;
    }
    dragging.value = true;

    const tableEl = tableRef.value;
    const tableLeft = tableEl!.getBoundingClientRect().left;
    const columnEl = event.target as HTMLElement;
    const columnRect = columnEl!.getBoundingClientRect();

    const columnKey = columnEl.dataset.name as string;

    const minLeft = columnRect.left - tableLeft + 30;

    dragState.value = {
      startMouseLeft: event.clientX,
      startLeft: columnRect.right - tableLeft,
      startColumnLeft: columnRect.left - tableLeft,
      tableLeft,
    };
    const resizeProxy = tableColumnResizeRef.value as HTMLElement;
    resizeProxy.style.display = 'block';
    resizeProxy.style.left = `${dragState.value.startLeft}px`;

    document.onselectstart = function () {
      return false;
    };
    document.ondragstart = function () {
      return false;
    };

    const handleMouseMove = (event: MouseEvent) => {
      const deltaLeft = event.clientX - dragState.value.startMouseLeft;
      const proxyLeft = dragState.value.startLeft + deltaLeft;
      resizeProxy.style.display = 'block';
      resizeProxy.style.left = `${Math.max(minLeft, proxyLeft)}px`;
    };

    const handleMouseUp = () => {
      if (dragging.value) {
        const { startColumnLeft } = dragState.value;
        const finalLeft = Number.parseInt(resizeProxy.style.left, 10);
        const latestColumnWidth = Math.ceil(Math.max(finalLeft - startColumnLeft, 80));

        const nextSiblingEl = columnEl!.nextElementSibling as HTMLElement;

        if (nextSiblingEl!.classList.contains('table-column-resize')) {
          return;
        }

        resizeProxy.style.display = 'none';
        document.body.style.cursor = '';
        dragging.value = false;

        const realWidth = Math.max(
          columnSizeConfig.value[columnKey].minWidth || 60,
          Math.min(latestColumnWidth, columnSizeConfig.value[columnKey].maxWidth || 1000000),
        );
        const renderColumWidthTotal = Array.from(columnEl.parentElement!.children).reduce((result, element) => {
          if (element === columnEl) {
            return result;
          }
          return result + element.getBoundingClientRect().width;
        }, 0);

        const tableWidth = tableRef.value!.getBoundingClientRect().width;

        if (renderColumWidthTotal + realWidth < tableWidth) {
          columnSizeConfig.value[columnKey].renderWidth = tableWidth - renderColumWidthTotal;
        } else {
          columnSizeConfig.value[columnKey].renderWidth = realWidth;
        }
      }

      dragable = false;

      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.onselectstart = null;
      document.ondragstart = null;
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleMouseMove = (event: MouseEvent) => {
    const target = (event.target as HTMLElement).closest('th');

    if (!target) {
      return;
    }

    const columnKey = target.dataset.name as string;

    const targetColumn = _.find(columnList.value, (column) => column.key === columnKey);
    if (!targetColumn || !targetColumn.props.resizeable) {
      return;
    }

    const rect = target!.getBoundingClientRect();

    const bodyStyle = document.body.style;
    if (rect.width > 12 && rect.right - event.pageX < 16) {
      bodyStyle.cursor = 'col-resize';
      bodyStyle.userSelect = 'none';
      dragable = true;
    } else if (!dragging.value) {
      bodyStyle.cursor = '';
      bodyStyle.userSelect = '';
      dragable = false;
    }
  };

  const handleOuterMousemove = _.throttle((event: Event) => {
    let i = event.composedPath().length - 1;
    while (i >= 0) {
      const target = event.composedPath()[i] as HTMLElement;
      if (target.classList && target.classList.contains('bk-editable-table')) {
        return;
      }
      i = i - 1;
    }
    document.body.style.cursor = '';
  }, 500);

  onMounted(() => {
    document.addEventListener('mousemove', handleOuterMousemove);
  });

  onBeforeUnmount(() => {
    document.removeEventListener('mousemove', handleOuterMousemove);
  });

  return {
    columnSizeConfig,
    handleMouseDown,
    handleMouseMove,
  };
}
