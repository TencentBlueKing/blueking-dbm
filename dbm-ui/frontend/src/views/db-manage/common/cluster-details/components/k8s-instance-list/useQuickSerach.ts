import _ from 'lodash';
import { useI18n } from 'vue-i18n';

import { clusterK8sInstStatus } from '@common/const';
import { ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});

  const quickSearchData = _.filter(
    [
      {
        id: 'pod_name',
        name: t('实例'),
        type: 'multiple-input',
        validator: (value: any) => {
          return !ipv4.test(value);
        },
      },
      {
        id: 'node',
        name: 'IP',
        type: 'multiple-input',
        validator: (value: any) => {
          return ipv4.test(value);
        },
      },
      {
        id: 'status',
        list: Object.entries(clusterK8sInstStatus).map(([key, statusItem]) => ({
          label: statusItem.text,
          value: key,
        })),
        name: t('状态'),
        type: 'multiple',
      },
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  const handleMergeSearchParams = (currentParams: Record<string, any>) => {
    const currentParamsCopy = { ...currentParams };
    const searchValueParams = searchValue.value;
    const quickSearchDataIds = quickSearchData.map((item) => item.id);

    const filteredParams = _.omitBy(
      currentParamsCopy,
      (value, key) => quickSearchDataIds.includes(key) && !Object.prototype.hasOwnProperty.call(searchValueParams, key),
    );

    return Object.assign({}, filteredParams, searchValueParams);
  };

  return {
    handleMergeSearchParams,
    quickSearchData,
    searchValue,
  };
};
