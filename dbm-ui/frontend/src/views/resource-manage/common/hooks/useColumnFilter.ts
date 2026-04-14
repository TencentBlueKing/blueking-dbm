import dayjs from 'dayjs';
import { markRaw, shallowRef, type UnwrapRef } from 'vue';
import { useRequest } from 'vue-request';

import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
import { queryDirtyMachineAttrs } from '@services/source/dbbase';
import { getUserList } from '@services/source/user';

import { specialOptionLabelMap, SpecialOptions } from '@common/const';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { t } from '@/locales';

const dirtyMachineAttrs = ['city', 'sub_zone', 'os_name', 'device_class'] as const;

export const useColumnFilter = (pool?: ServiceParameters<typeof queryDirtyMachineAttrs>['pool']) => {
  const baseFilter = {
    ips: {
      component: markRaw(MultipleInput),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        placeholder: t('请输入 IP'),
      },
      showConfirmAndReset: true,
    },
    pool: {
      component: markRaw(MultipleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: Object.entries(FaultOrRecycleMachineModel.poolTextMap).map(([key, value]) => ({
          label: value,
          value: key,
        })),
      },
      showConfirmAndReset: true,
    },
    rack_id: {
      component: markRaw(MultipleInput),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        placeholder: t('请输入 IP'),
      },
      showConfirmAndReset: true,
    },
    update_at: {
      component: markRaw(DatetimeRange),
      name: t('操作时间'),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
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
      showConfirmAndReset: true,
    },
    updater: {
      component: markRaw(MultipleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
          const requestParams = {};
          if (params.defaultValue) {
            Object.assign(requestParams, { exact_lookups: params.defaultValue });
          }
          if (params.keyword) {
            Object.assign(requestParams, { fuzzy_lookups: params.keyword });
          }
          return getUserList(requestParams).then((res) =>
            res.results.map((item) => ({
              label: `${item.username} (${item.display_name})`,
              value: item.username,
            })),
          );
        },
        remoteSearch: true,
      },
      showConfirmAndReset: true,
    },
  } as const;

  const data = shallowRef<{
    [K in keyof typeof baseFilter | (typeof dirtyMachineAttrs)[number]]: {
      component: any;
      popupProps: {
        attach: 'body';
        placement: 'bottom';
      };
      props: Record<string, any>;
      showConfirmAndReset?: boolean;
    };
  }>();

  useRequest(queryDirtyMachineAttrs, {
    defaultParams: [
      {
        machine_attrs: dirtyMachineAttrs.join(','),
        pool,
      },
    ],
    onSuccess(result) {
      data.value = dirtyMachineAttrs.reduce(
        (res, attr) => {
          const getList = () => {
            const formatList = (result[attr] || []).map((item) => ({
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
          };

          return Object.assign(res, {
            [attr]: {
              component: markRaw(MultipleSelect),
              popupProps: {
                attach: 'body',
                placement: 'bottom',
              },
              props: {
                list: getList(),
              },
              showConfirmAndReset: true,
            },
          });
        },
        {} as NonNullable<UnwrapRef<typeof data>>,
      );
      data.value = {
        ...baseFilter,
        ...data.value,
      };
    },
  });

  return {
    data,
  };
};
