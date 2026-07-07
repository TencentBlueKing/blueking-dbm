import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import SurrealdbHaInstanceModel from '@services/model/surrealdb/surrealdb-ha-instance';

import { clusterInstStatus } from '@common/const';
import { ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(searchValue.value).length > 0);

  const quickSearchData = _.filter(
    [
      {
        id: 'podName',
        name: t('实例'),
        type: 'multiple-input',
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
        list: Object.entries(clusterInstStatus).map(([key, statusItem]) => ({
          label: statusItem.text,
          value: key,
        })),
        name: t('状态'),
        type: 'multiple',
      },
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  const handleFilterList = (tableOriginalData: SurrealdbHaInstanceModel[]) => {
    const localSearchValue = searchValue.value;

    if (Object.keys(localSearchValue).length === 0) {
      return tableOriginalData;
    }

    return tableOriginalData.filter((tableOriginalDataItem) => {
      if (Object.prototype.hasOwnProperty.call(localSearchValue, 'podName')) {
        const podNameList = localSearchValue.podName.split(',');
        return podNameList.includes(tableOriginalDataItem.podName);
      }
      if (Object.prototype.hasOwnProperty.call(localSearchValue, 'node')) {
        const nodeList = localSearchValue.node.split(',');
        return nodeList.includes(tableOriginalDataItem.node);
      }
      if (Object.prototype.hasOwnProperty.call(localSearchValue, 'status')) {
        const statusList = localSearchValue.status.split(',');
        return statusList.includes(tableOriginalDataItem.status.toLowerCase());
      }

      return true;
    });
  };

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
    handleFilterList,
    handleMergeSearchParams,
    isSearching,
    quickSearchData,
    searchValue,
  };
};
