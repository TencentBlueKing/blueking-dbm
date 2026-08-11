import type { PrimaryTableCol } from 'tdesign-vue-next';

import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

import { t } from '@locales/index';

interface ResourceItem {
  tags: { key: string; value: string }[];
}

export const tagsColumn: PrimaryTableCol = {
  cell: (_, { row }) => {
    const tipList = (row as ResourceItem).tags.map((tag) => `${tag.key}: ${tag.value}`);
    return tipList.length ? <TextOverflowLayout>{tipList.join(' , ')}</TextOverflowLayout> : '--';
  },
  colKey: 'tag',
  minWidth: 110,
  title: t('标签'),
};

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
