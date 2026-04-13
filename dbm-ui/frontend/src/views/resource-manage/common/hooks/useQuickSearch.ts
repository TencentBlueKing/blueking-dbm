import dayjs from 'dayjs';
import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
import { queryDirtyMachineAttrs } from '@services/source/dbbase';
import { getUserList } from '@services/source/user';

import { specialOptionLabelMap, SpecialOptions } from '@common/const';
import { ipPort, ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

const dirtyMachineAttrs = ['city', 'sub_zone', 'os_name', 'device_class'] as const;

export const useQuickSearch = (pool?: ServiceParameters<typeof queryDirtyMachineAttrs>['pool']) => {
  const { t } = useI18n();

  const quickSearchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const getDirtyMachineAttrs = (attr: (typeof dirtyMachineAttrs)[number]) => {
    return queryDirtyMachineAttrs({
      machine_attrs: dirtyMachineAttrs.join(','),
      pool,
    }).then((data) => {
      const formatList = data[attr].map((item) => ({
        label: item.text,
        value: item.value,
      }));

      if (dirtyMachineAttrs.includes(attr)) {
        const filterList = formatList.filter((item) => item.value !== null && item.value !== '');
        if (filterList.length !== formatList.length) {
          return filterList.concat({
            label: specialOptionLabelMap[SpecialOptions.EMPTY],
            value: SpecialOptions.EMPTY,
          });
        }
        return filterList;
      }

      return formatList;
    });
  };

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
      !pool && {
        id: 'pool',
        list: Object.entries(FaultOrRecycleMachineModel.poolTextMap).map(([key, value]) => ({
          label: value,
          value: key,
        })),
        name: t('所属池'),
        type: 'multiple',
      },
      {
        id: 'city',
        name: t('地域'),
        remoteMethod: () => getDirtyMachineAttrs('city'),
        type: 'multiple',
      },
      {
        id: 'sub_zone',
        name: t('园区'),
        remoteMethod: () => getDirtyMachineAttrs('sub_zone'),
        type: 'multiple',
      },
      {
        id: 'rack_id',
        name: t('机架'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !ipPort.test(value) && !ipv4.test(value);
        },
      },
      {
        id: 'os_name',
        name: t('操作系统'),
        remoteMethod: () => getDirtyMachineAttrs('os_name'),
        type: 'multiple',
      },
      {
        id: 'device_class',
        name: t('机型'),
        remoteMethod: () => getDirtyMachineAttrs('device_class'),
        type: 'multiple',
      },
      pool && {
        id: 'update_at',
        name: t('转入时间'),
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
      pool && {
        id: 'updater',
        name: t('转入人'),
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

  return {
    isSearching,
    quickSearchData,
    quickSearchValue,
  };
};
