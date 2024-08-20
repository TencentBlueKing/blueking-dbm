/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import _ from 'lodash';
import { type Ref } from 'vue';

export default function (tableRef: Ref<Element>, tableColumnResizeRef: Ref<HTMLElement>, mouseupCallback: () => void) {
  let dragable = false;

  const dragging = ref(false);
  const dragState = ref({} as any);

  const initColumnWidth = () => {
    setTimeout(() => {
      const tableEl = tableRef.value;
      tableEl.querySelectorAll('th').forEach((columnEl) => {
        const isFixed = columnEl.getAttribute('data-fixed');
        const { width } = columnEl.getBoundingClientRect();
        const renderWidth = Math.max(parseInt(columnEl.getAttribute('data-minWidth') || '', 10), width);
        if (isFixed) {
          const fixedWidth = columnEl.getAttribute('data-width');
          // eslint-disable-next-line no-param-reassign
          columnEl.style.width = `${fixedWidth}px`;
        } else {
          const maxWidth = Number(columnEl.getAttribute('data-maxWidth'));
          if (maxWidth && renderWidth > maxWidth) {
            // eslint-disable-next-line no-param-reassign
            columnEl.style.width = `${maxWidth}px`;
          } else {
            // eslint-disable-next-line no-param-reassign
            columnEl.style.width = `${renderWidth}px`;
          }
        }
      });
    });
  };

  const handleMouseDown = (
    event: MouseEvent,
    payload: {
      columnKey: string;
      minWidth: number;
    },
  ) => {
    if (!dragable) {
      return;
    }
    const { columnKey, minWidth = 100 } = payload;
    const target = (event.target as Element).closest('th') as Element;
    const tableEl = tableRef.value;
    const columnEl = tableEl.querySelector(`th.column-${columnKey}`) as HTMLElement;
    const tableLeft = tableEl.getBoundingClientRect().left;
    const columnRect = columnEl.getBoundingClientRect();
    const minLeft = columnRect.left - tableLeft + 30;
    const scrollLetf = tableRef.value.scrollLeft;
    dragState.value = {
      startMouseLeft: event.clientX,
      startLeft: columnRect.right - tableLeft + scrollLetf,
      startColumnLeft: columnRect.left - tableLeft,
      tableLeft,
    };
    const resizeProxy = tableColumnResizeRef.value;
    let resizeProxyLeft = dragState.value.startLeft;
    resizeProxy.style.display = 'block';
    resizeProxy.style.left = `${resizeProxyLeft}px`;

    document.onselectstart = function () {
      return false;
    };
    document.ondragstart = function () {
      return false;
    };

    const handleMouseMove = (event: MouseEvent) => {
      dragging.value = true;
      const deltaLeft = event.clientX - dragState.value.startMouseLeft;
      const proxyLeft = dragState.value.startLeft + deltaLeft;
      resizeProxy.style.display = 'block';
      resizeProxyLeft = Math.max(minLeft, proxyLeft);
      resizeProxy.style.left = `${resizeProxyLeft}px`;
      target.classList.add('poiner-right');
    };

    const handleMouseUp = () => {
      if (dragging.value) {
        const { startColumnLeft } = dragState.value;
        const columnWidth = Math.max(resizeProxyLeft - startColumnLeft - scrollLetf, minWidth);
        columnEl.style.width = `${columnWidth}px`;
        resizeProxy.style.display = 'none';
        document.body.style.cursor = '';
        dragging.value = false;
        dragState.value = {};
      }
      resizeProxy.style.display = 'none';
      dragable = false;
      mouseupCallback();
      initColumnWidth();
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.onselectstart = null;
      document.ondragstart = null;
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleMouseMove = (event: MouseEvent) => {
    if (dragging.value) {
      return;
    }

    const target = (event.target as Element).closest('th') as Element;
    const rect = target.getBoundingClientRect();
    const bodyStyle = document.body.style;
    if (rect.width > 12 && rect.right - event.pageX < 8) {
      bodyStyle.cursor = 'col-resize';
      dragable = true;
      target.classList.add('poiner-right');
    } else if (!dragging.value) {
      bodyStyle.cursor = '';
      dragable = false;
      target.classList.remove('poiner-right');
      target.previousElementSibling?.classList.remove('poiner-right');
    }
  };

  const handleOuterMousemove = _.throttle((event) => {
    let i = event.composedPath().length - 1;
    while (i >= 0) {
      if (event.composedPath()[i].id === 'toolboxRenderTableKey') {
        return;
      }
      i = i - 1;
    }
    document.body.style.cursor = '';
  }, 100);

  provide('toolboxRenderTableKey', {
    columnMousedown: handleMouseDown,
    columnMouseMove: handleMouseMove,
  });

  onMounted(() => {
    initColumnWidth();
    document.addEventListener('mousemove', handleOuterMousemove);
  });

  onBeforeUnmount(() => {
    document.removeEventListener('mousemove', handleOuterMousemove);
  });

  return {
    initColumnWidth,
    handleMouseDown,
    handleMouseMove,
  };
}
