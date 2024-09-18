import { onMounted, ref, useTemplateRef } from 'vue';

import { getOffset } from '@utils';

export default () => {
  const tableRef = useTemplateRef<HTMLElement>('table');
  const tableMaxHeight = ref<number | 'auto'>('auto');

  onMounted(() => {
    const { top } = getOffset(tableRef.value as HTMLElement);
    const totalHeight = window.innerHeight;
    const tableHeaderHeight = 42;
    const paginationHeight = 60;
    const pageOffsetBottom = 20;
    const tableRowHeight = 42;

    const tableRowTotalHeight = totalHeight - top - tableHeaderHeight - paginationHeight - pageOffsetBottom;

    const rowNum = Math.max(Math.floor(tableRowTotalHeight / tableRowHeight), 5);

    tableMaxHeight.value = tableHeaderHeight + rowNum * tableRowHeight + paginationHeight + 3;
  });

  return {
    tableRef,
    tableMaxHeight,
  };
};
