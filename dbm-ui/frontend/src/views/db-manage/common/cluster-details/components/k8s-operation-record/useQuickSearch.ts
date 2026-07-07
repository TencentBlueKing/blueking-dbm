import dayjs from 'dayjs';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import KubernetesOperationLogModel from '@services/model/kubernetes/kubernetes-operation-log';
import { getUserList } from '@services/source/user';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();

  const quickSearchValue = ref<Record<string, string>>({
    createdAt: `${dayjs().subtract(6, 'day').startOf('day').format('YYYY-MM-DD HH:mm:ss')},${dayjs().endOf('day').format('YYYY-MM-DD HH:mm:ss')}`,
  });
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const quickSearchData = [
    {
      id: 'requestType',
      list: Object.entries(KubernetesOperationLogModel.RequestTypeMap).map(([key, label]) => ({
        label,
        value: key,
      })),
      name: t('操作类型'),
      type: 'multiple',
    },
    {
      id: 'creator',
      name: t('操作人'),
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
      id: 'createdAt',
      name: t('操作时间'),
      props: {
        shortcuts: [
          {
            text: t('近 1 小时'),
            value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('近 12 小时'),
            value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('今天'),
            value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 7 天'),
            value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 1 个月'),
            value: () => [dayjs().subtract(1, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 3 个月'),
            value: () => [dayjs().subtract(3, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 6 个月'),
            value: () => [dayjs().subtract(6, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
        ],
      },
      type: 'datetime-range',
    },
  ] as QuickSearchProps['data'];

  return {
    isSearching,
    quickSearchData,
    quickSearchValue,
  };
};
