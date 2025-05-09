import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

import { t } from '@locales/index';

interface ResourceItem {
  tags: { key: string; value: string }[];
}

export const tagsColumn = {
  field: 'tag',
  label: t('标签'),
  minWidth: 110,
  render: ({ data }: { data: ResourceItem }) => {
    const tipList = data.tags.map((tag) => `${tag.key}: ${tag.value}`);
    return <TextOverflowLayout>{tipList.join(' , ')}</TextOverflowLayout>;
  },
};

// TODO: 后续选择器的其他公共列也抽取到这里来
