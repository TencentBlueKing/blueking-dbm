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
        width: number;
        minWidth: number;
        maxWidth: number;
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
      const columnSizeConfigCache = { ...columnSizeConfig.value };
      columnSizeConfig.value = columnList.value.reduce((result, columnConfig) => {
        const width = columnConfig.props.width || 0;
        const minWidth =
          Number(columnConfig.props.minWidth) > 60 ? Number(columnConfig.props.minWidth) : Number.MIN_VALUE;
        const maxWidth =
          Number(columnConfig.props.maxWidth) > 60 ? Number(columnConfig.props.maxWidth) : Number.MAX_VALUE;

        const renderWidth = Math.min(Math.max(width, minWidth), maxWidth);

        Object.assign(result, {
          [columnConfig.key]: columnSizeConfigCache[columnConfig.key]
            ? columnSizeConfigCache[columnConfig.key]
            : {
                width,
                minWidth,
                maxWidth,
                renderWidth,
              },
        });

        return result;
      }, {});
      console.log('columnSizeConfig.value = ', columnSizeConfig.value);
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
        const containerWidth = tableEl!.getBoundingClientRect().width;
        const containerScrollWidth = tableEl!.scrollWidth;
        const isScrolling = containerScrollWidth > containerWidth;
        const { startColumnLeft } = dragState.value;
        const finalLeft = Number.parseInt(resizeProxy.style.left, 10);
        const latestColumnWidth = Math.ceil(Math.max(finalLeft - startColumnLeft, 60));

        const nextSiblingEl = columnEl!.nextElementSibling as HTMLElement;

        if (nextSiblingEl!.classList.contains('table-column-resize')) {
          return;
        }
        // 没有出现滚动条时缩小当前列的宽度同时会放大后面一列的宽度
        if (!isScrolling && columnRect.width > latestColumnWidth) {
          const latestWidth = columnRect.width - latestColumnWidth + nextSiblingEl!.getBoundingClientRect().width;
          console.log('latestWidth = ', latestWidth);
        }

        resizeProxy.style.display = 'none';
        document.body.style.cursor = '';
        dragging.value = false;

        const realWidth = Math.max(
          columnSizeConfig.value[columnKey].minWidth as number,
          Math.min(latestColumnWidth, columnSizeConfig.value[columnKey].maxWidth as number),
        );
        columnSizeConfig.value[columnKey].renderWidth = realWidth;
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
