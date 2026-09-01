import dayjs from 'dayjs';
import { markRaw, shallowRef } from 'vue';

import KubernetesOperationLogModel from '@services/model/kubernetes/kubernetes-operation-log';
import { getUserList } from '@services/source/user';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { t } from '@/locales';

export const useColumnFilter = () => {
  const baseFilter = {
    createdAt: {
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
    creator: {
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
    requestType: {
      component: markRaw(MultipleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: Object.entries(KubernetesOperationLogModel.RequestTypeMap).map(([key, label]) => ({
          label,
          value: key,
        })),
      },
      showConfirmAndReset: true,
    },
  } as const;

  const data = shallowRef<{
    [K in keyof typeof baseFilter]: {
      component: any;
      popupProps: {
        attach: 'body';
        placement: 'bottom';
      };
      props: Record<string, any>;
      showConfirmAndReset?: boolean;
    };
  }>();

  data.value = {
    ...baseFilter,
  };

  return {
    data,
  };
};
