import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

// import { listTag } from '@services/source/tag';
import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

import BizDbaModel from './bizDba';

export const useQuickSearch = (status: Ref<'all' | 'assigned' | 'unassigned'>) => {
  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();

  const searchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(searchValue.value).length > 0);

  const quickSearchData = _.filter(
    [
      {
        id: 'bk_biz_id',
        name: t('业务 ID'),
        // type: 'input',
      },
      {
        id: 'name',
        list: globalBizStore.bizs.map((item) => ({ label: item.name, value: item.name })),
        name: t('业务名称'),
        type: 'multiple',
      },
      // {
      //   id: 'tags',
      //   name: t('标签'),
      //   remoteMethod: () => {
      //     return listTag({
      //       limit: -1,
      //       offset: 0,
      //       // type: 'app',
      //       type: 'resource',
      //     }).then((data) =>
      //       data.results.map((item) => ({
      //         label: item.value,
      //         value: item.id,
      //       })),
      //     );
      //   },
      //   remoteSearch: true,
      //   type: 'multiple',
      // },
      {
        id: 'users',
        name: t('人员名称'),
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
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  const handleFilterList = (tableOriginalData: BizDbaModel[]) => {
    const localSearchValue = searchValue.value;

    if (Object.keys(localSearchValue).length === 0 && !status.value) {
      return tableOriginalData;
    }

    return tableOriginalData.filter((tableOriginalDataItem) => {
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'bk_biz_id') &&
        tableOriginalDataItem.bk_biz_id !== Number(localSearchValue.bk_biz_id)
      ) {
        return false;
      }
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'name') &&
        !tableOriginalDataItem.name.includes(localSearchValue.name)
      ) {
        return false;
      }
      if (Object.prototype.hasOwnProperty.call(localSearchValue, 'users')) {
        const userMap = Object.fromEntries(localSearchValue.users.split(',').map((item) => [item, true]));
        const rowUsers = [
          tableOriginalDataItem.primary_dba,
          tableOriginalDataItem.standby_dba,
          ...tableOriginalDataItem.level2_dba,
        ];
        if (rowUsers.every((userItem) => !userMap[userItem])) {
          return false;
        }
      }
      if (status.value !== 'all') {
        if (status.value === 'assigned') {
          return tableOriginalDataItem.isAssigned;
        } else {
          return !tableOriginalDataItem.isAssigned;
        }
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
