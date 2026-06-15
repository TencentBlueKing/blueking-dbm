import dayjs from 'dayjs';
import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { dbaOperateTypesInfo, dbaRoleTypesInfo, DBTypeInfos } from '@common/const';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = (isPlatform: boolean) => {
  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();

  const quickSearchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const quickSearchData = _.filter(
    [
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
        id: 'create_at',
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
      isPlatform && {
        id: 'bk_biz_id',
        list: globalBizStore.bizs.map((item) => ({ label: item.name, value: item.bk_biz_id })),
        name: t('所属业务'),
        type: 'multiple',
      },
      {
        id: 'operate_type',
        list: Object.values(dbaOperateTypesInfo).map((item) => ({ label: item.text, value: item.id })),
        name: t('操作类型'),
        type: 'multiple',
      },
      {
        id: 'db_type',
        list: Object.values(DBTypeInfos).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        name: t('DB类型'),
        type: 'multiple',
      },
      {
        id: 'role',
        list: Object.values(dbaRoleTypesInfo).map((item) => ({
          label: item.text,
          value: item.id,
        })),
        name: t('变更角色'),
        type: 'multiple',
      },
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  return {
    isSearching,
    quickSearchData,
    quickSearchValue,
  };
};
