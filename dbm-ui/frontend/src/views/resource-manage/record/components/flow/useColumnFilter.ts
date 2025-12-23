import dayjs from 'dayjs';
import { markRaw, shallowRef, type UnwrapRef } from 'vue';

import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { machineEventsDisplayMap } from '@common/const';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
import SingleSelect from '@components/db-table/components/SingleSelect.vue';

import { t } from '@/locales';

export const useColumnFilter = () => {
  const globalBizStore = useGlobalBizs();

  const baseFilter = {
    bk_biz_id: {
      component: markRaw(SingleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: globalBizStore.bizs.map((item) => ({ label: item.name, value: item.bk_biz_id })),
      },
      showConfirmAndReset: true,
    },
    create_at: {
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
    domain: {
      component: markRaw(MultipleInput),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        placeholder: t('请输入集群'),
      },
      showConfirmAndReset: true,
    },
    events: {
      component: markRaw(MultipleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: Object.entries(machineEventsDisplayMap).map(([key, value]) => ({ label: value, value: key })),
      },
      showConfirmAndReset: true,
    },
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
    ticket_id: {
      component: markRaw(MultipleInput),
      name: t('关联单据'),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        autofocus: true,
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
    ...(baseFilter as NonNullable<UnwrapRef<typeof data>>),
  };

  return {
    data,
  };
};
