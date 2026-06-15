import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { listTag } from '@services/source/tag';
import type { BizItem } from '@services/types';

// import { useGlobalBizs } from '@stores';
import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();
  // const globalBizStore = useGlobalBizs();

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
        // list: globalBizStore.bizs
        //   .filter((item) => item.status === 'managed')
        //   .map((item) => ({ label: item.name, value: item.name })),
        name: t('业务名称'),
        // type: 'multiple',
      },
      {
        id: 'english_name',
        // list: globalBizStore.bizs
        //   .filter((item) => item.status === 'managed')
        //   .map((item) => ({ label: item.english_name, value: item.english_name })),
        name: t('业务 Code'),
        // type: 'multiple',
      },
      {
        id: 'tags',
        name: t('标签'),
        remoteMethod: () => {
          return listTag({
            limit: -1,
            offset: 0,
            type: 'app',
          }).then((data) =>
            data.results.map((item) => ({
              label: item.value,
              value: item.id,
            })),
          );
        },
        remoteSearch: true,
        type: 'multiple',
      },
      // {
      //   id: 'updater',
      //   name: t('操作人'),
      //   remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
      //     const requestParams = {};
      //     if (params.defaultValue) {
      //       Object.assign(requestParams, { exact_lookups: params.defaultValue });
      //     }
      //     if (params.keyword) {
      //       Object.assign(requestParams, { fuzzy_lookups: params.keyword });
      //     }

      //     return getUserList(requestParams).then((data) =>
      //       data.results.map((item) => ({
      //         label: `${item.username} (${item.display_name})`,
      //         value: item.username,
      //       })),
      //     );
      //   },
      //   remoteSearch: true,
      //   type: 'multiple',
      // },
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  const handleFilterList = (tableOriginalData: BizItem[]) => {
    const localSearchValue = searchValue.value;

    if (Object.keys(localSearchValue).length === 0) {
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
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'english_name') &&
        !tableOriginalDataItem.english_name.includes(localSearchValue.english_name)
      ) {
        return false;
      }
      if (Object.prototype.hasOwnProperty.call(localSearchValue, 'tags')) {
        const tagMap = Object.fromEntries(localSearchValue.tags.split(',').map((item) => [item, true]));
        if (tableOriginalDataItem.tags.every((tagItem) => !tagMap[tagItem.id])) {
          return false;
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
