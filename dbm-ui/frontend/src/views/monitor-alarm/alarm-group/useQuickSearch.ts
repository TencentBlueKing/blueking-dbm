import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import NoticGroupModel from '@services/model/notice-group/notice-group';
import { getUserList } from '@services/source/user';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();

  const quickSearchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const quickSearchData = [
    {
      id: 'name',
      name: t('告警组名称'),
      type: 'input',
    },
    // {
    //   id: 'is_built_in',
    //   list: [
    //     {
    //       label: t('内置'),
    //       value: 'true',
    //     },
    //     {
    //       label: t('自定义'),
    //       value: 'false',
    //     },
    //   ],
    //   name: t('类型'),
    //   type: 'single',
    // },
    {
      id: 'receivers',
      name: t('通知对象'),
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
    {
      id: 'notice_ways',
      list: NoticGroupModel.NoticeMethodList.map((item) => ({
        label: item.label,
        value: item.type,
      })),
      name: t('通知方式'),
      type: 'multiple',
    },
  ] as QuickSearchProps['data'];

  return {
    isSearching,
    quickSearchData,
    quickSearchValue,
  };
};
