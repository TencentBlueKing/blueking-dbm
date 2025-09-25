import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketGroupTypes } from '@services/source/ticket';
import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultCascader from '@components/db-table/components/MultCascader.vue';
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
    type?: 'multiple' | 'single' | 'input';
  }
>;

export default () => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const tableFilter = computed<ITableFilter>(() => {
    return {
      bk_biz_ids: {
        component: markRaw(MultipleSelect),
        name: t('业务'),
        props: {
          list: globalBizsStore.bizs.map((item) => ({
            label: item.name,
            value: `${item.bk_biz_id}`,
          })),
        },
        showConfirmAndReset: true,
      },
      cluster: {
        component: markRaw(MultipleInput),
        name: t('集群'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
      },
      create_at: {
        component: markRaw(DatetimeRange),
        name: t('申请时间'),
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
      creator__in: {
        component: markRaw(MultipleSelect),
        name: t('申请人'),
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
      ids: {
        component: markRaw(MultipleInput),
        name: t('单号'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
      },
      remark: {
        name: t('备注'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      status: {
        component: markRaw(MultipleSelect),
        name: t('单据状态'),
        props: {
          list: Object.keys(TicketModel.statusTextMap).reduce<Record<'label' | 'value', string>[]>((acc, key) => {
            acc.push({
              label: TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap],
              value: key,
            });
            return acc;
          }, []),
        },
        showConfirmAndReset: true,
      },
      ticket_type: {
        component: markRaw(MultCascader),
        name: t('单据类型'),
        props: {
          remoteMethod: getTicketGroupTypes,
        },
        showConfirmAndReset: true,
      },
    };
  });

  return tableFilter;
};
