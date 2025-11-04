import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';

import RedisKeystatAnalysisModel from '@services/model/redis/redis-keystat-analysis';
import { getUserList } from '@services/source/user';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

type ITableFilter = Record<
  string,
  {
    component?: any;
    confirmEvents?: string[];
    list?:
      | {
          label: string;
          value: string;
        }[]
      | {
          children: {
            label: string;
            value: string;
          }[];
          label: string;
          value: string;
        }[];
    name: string;
    props?: Record<string, any>;
    showConfirmAndReset: boolean;
    type?: 'multiple' | 'single' | 'input';
  }
>;

export default () => {
  const { t } = useI18n();

  const tableFilter = computed<ITableFilter>(() => {
    return {
      create_at: {
        component: markRaw(DatetimeRange),
        name: t('执行时间'),
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
      immute_domain: {
        component: markRaw(MultipleInput),
        name: t('集群'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        showConfirmAndReset: true,
      },
      instance_addresses: {
        component: markRaw(MultipleInput),
        name: t('实例'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        showConfirmAndReset: true,
      },
      operator: {
        component: markRaw(MultipleSelect),
        name: t('创建人'),
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
      status: {
        component: markRaw(MultipleSelect),
        name: t('状态'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        props: {
          list: Object.keys(RedisKeystatAnalysisModel.STATUS_TEXT_MAP).reduce<Record<'label' | 'value', string>[]>(
            (acc, key) => {
              acc.push({
                label:
                  RedisKeystatAnalysisModel.STATUS_TEXT_MAP[
                    key as keyof typeof RedisKeystatAnalysisModel.STATUS_TEXT_MAP
                  ],
                value: key,
              });
              return acc;
            },
            [],
          ),
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
        showConfirmAndReset: true,
      },
    };
  });

  return tableFilter;
};
