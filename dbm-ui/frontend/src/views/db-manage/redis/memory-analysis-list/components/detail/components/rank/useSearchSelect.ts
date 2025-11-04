import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

export default () => {
  const { t } = useI18n();

  const quickSearchValue = ref<Record<string, any>>({});

  const quickSearchData = computed(() => {
    const serachList: Props['data'] = [
      {
        id: 'key_type',
        name: t('Key 类型'),
        type: 'input',
      },
      {
        description: t('支持模糊搜索'),
        id: 'key_name',
        name: t('Key 样本'),
        type: 'input',
      },
    ] as const;

    return serachList;
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });

  return {
    quickSearchData,
    quickSearchValue,
  };
};
