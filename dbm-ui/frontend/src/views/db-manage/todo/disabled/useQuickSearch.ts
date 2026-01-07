import dayjs from 'dayjs';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { ipPort, ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();

  const quickSearchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const quickSearchData = [
    {
      description: t('单个值支持模糊搜索'),
      id: 'immute_domain',
      name: t('集群'),
      type: 'input',
      validator: (value: string) => {
        return !ipPort.test(value) && !ipv4.test(value);
      },
    },
    {
      id: 'cluster_id',
      name: 'ID',
      type: 'multiple-input',
      validator: (value: string) => {
        return !isNaN(Number(value)) ? true : t('ID 只支持数字');
      },
    },
    {
      id: 'bk_biz_id',
      list: globalBizStore.bizs.map((item) => ({ label: item.name, value: item.bk_biz_id })),
      name: t('所属业务'),
      type: 'multiple',
    },
    {
      id: 'create_at',
      name: t('禁用时间'),
      props: {
        shortcuts: [
          {
            text: t('今天'),
            value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 3 天'),
            value: () => [dayjs().subtract(2, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 7 天'),
            value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('超过 7 天'),
            value: () => [dayjs(0).startOf('day').toDate(), dayjs().subtract(7, 'day').endOf('day').toDate()],
          },
        ],
      },
      type: 'datetime-range',
    },
    {
      id: 'disable_person',
      name: t('禁用人'),
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
