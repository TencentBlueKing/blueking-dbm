import dayjs from 'dayjs';
import { markRaw, shallowRef } from 'vue';

import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { t } from '@/locales';

export const useColumnFilter = () => {
  const globalBizStore = useGlobalBizs();

  const data = shallowRef<{
    [K in keyof typeof baseFilter]: {
      component?: any;
      popupProps: {
        attach: 'body';
        placement: 'bottom';
      };
      props: Record<string, any>;
      showConfirmAndReset?: boolean;
    };
  }>();

  const baseFilter = {
    bk_biz_id: {
      component: markRaw(MultipleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: globalBizStore.bizs.map((item) => ({ label: item.name, value: item.bk_biz_id })),
      },
      showConfirmAndReset: true,
    },
    cluster_id: {
      component: markRaw(MultipleInput),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        placeholder: t('请输入 ID'),
      },
      showConfirmAndReset: true,
    },
    create_at: {
      component: markRaw(DatetimeRange),
      name: t('禁用时间'),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
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
      showConfirmAndReset: true,
    },
    disable_person: {
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
    immute_domain: {
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        placeholder: t('请输入集群'),
      },
      showConfirmAndReset: true,
      type: 'input',
    },
  } as const;

  data.value = baseFilter;

  return {
    data,
  };
};
