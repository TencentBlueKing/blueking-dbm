import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();

  const quickSearchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const quickSearchData = [
    {
      id: 'bk_idc_city_name',
      name: t('地域'),
      type: 'input',
    },
    {
      id: 'bk_sub_zone',
      name: t('园区'),
      type: 'input',
    },
    {
      id: 'os_name',
      name: t('操作系统'),
      type: 'input',
    },
    {
      id: 'bk_svr_device_class_name',
      name: t('机型'),
      type: 'input',
    },
    {
      id: 'operator',
      name: t('主要负责人'),
      remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
        const requestParams = {};
        if (params.defaultValue) {
          Object.assign(requestParams, { exact_lookups: params.defaultValue });
        }
        if (params.keyword) {
          Object.assign(requestParams, { fuzzy_lookups: params.keyword });
        }

        return getUserList(requestParams).then((data) =>
          data.results.map((item) => ({
            label: `${item.username} (${item.display_name})`,
            value: item.username,
          })),
        );
      },
      remoteSearch: true,
      type: 'multiple',
    },
  ] as QuickSearchProps['data'];

  return {
    isSearching,
    quickSearchData,
    quickSearchValue,
  };
};
