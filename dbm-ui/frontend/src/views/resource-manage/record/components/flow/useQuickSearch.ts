import dayjs from 'dayjs';
import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { MachineEvents, machineEventsDisplayMap } from '@common/const';
import { ipPort, ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useQuickSearch = () => {
  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();

  const quickSearchValue = ref<Record<string, string>>({
    create_at: [
      dayjs().subtract(6, 'day').startOf('day').format('YYYY-MM-DD HH:mm:ss'),
      dayjs().endOf('day').format('YYYY-MM-DD HH:mm:ss'),
    ].join(','),
  });
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const quickSearchData = _.filter(
    [
      {
        id: 'ips',
        name: 'IP',
        type: 'multiple-input',
        validator: (value: string) => {
          return ipPort.test(value) || ipv4.test(value);
        },
      },
      {
        id: 'events',
        list: [
          MachineEvents.IMPORT_RESOURCE,
          MachineEvents.APPLY_RESOURCE,
          MachineEvents.RETURN_RESOURCE,
          MachineEvents.TO_FAULT,
          MachineEvents.TO_RECYCLE,
          MachineEvents.REMOVE_HOST,
          MachineEvents.RECYCLED,
          MachineEvents.UNDO_IMPORT,
          MachineEvents.HOST_ATTRIBUTE,
          MachineEvents.RESOURCE_OWNER,
        ].map((key) => ({ label: machineEventsDisplayMap[key], value: key })),
        name: t('操作类型'),
        type: 'multiple',
      },
      {
        id: 'updater',
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
      {
        id: 'bk_biz_id',
        list: globalBizStore.bizs.map((item) => ({ label: item.name, value: item.bk_biz_id })),
        name: t('所属业务'),
        type: 'single',
      },
      {
        id: 'ticket_id',
        name: t('关联单据'),
        type: 'multiple-input',
        validator: (value) => {
          return !isNaN(Number(value)) ? true : t('ID 只支持数字');
        },
      },
      {
        id: 'domain',
        name: t('集群'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !ipPort.test(value) && !ipv4.test(value);
        },
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
