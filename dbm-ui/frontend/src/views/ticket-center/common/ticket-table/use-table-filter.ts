import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketGroupTypes } from '@services/source/ticket';
import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultCascader from '@components/db-table/components/MultCascader.vue';

import MultipleSelect from '@/components/db-table/components/MultipleSelect.vue';

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

  const ticketTypeGroupList = shallowRef<
    {
      children: {
        label: string;
        value: string;
      }[];
      label: string;
      value: string;
    }[]
  >([]);

  const userList = shallowRef<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const tableFilter = computed<ITableFilter>(() => {
    return {
      bk_biz_ids: {
        list: globalBizsStore.bizs.map((item) => ({
          label: item.name,
          value: `${item.bk_biz_id}`,
        })),
        name: t('业务'),
        showConfirmAndReset: true,
        type: 'multiple',
      },
      cluster: {
        name: t('集群'),
        showConfirmAndReset: true,
        type: 'input',
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
      creator: {
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
                label: `${item.display_name} (${item.username})`,
                value: item.username,
              })),
            );
          },
          remoteSearch: true,
        },
        showConfirmAndReset: true,
      },
      ids: {
        name: t('单号'),
        showConfirmAndReset: true,
        type: 'input',
      },
      remark: {
        name: t('备注'),
        showConfirmAndReset: true,
        type: 'input',
      },
      status: {
        list: Object.keys(TicketModel.statusTextMap).reduce<Record<'label' | 'value', string>[]>((acc, key) => {
          acc.push({
            label: TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap],
            value: key,
          });
          return acc;
        }, []),
        name: t('单据状态'),
        showConfirmAndReset: true,
        type: 'multiple',
      },
      ticket_type: {
        component: markRaw(MultCascader),
        name: t('单据类型'),
        props: {
          list: ticketTypeGroupList.value,
        },
        showConfirmAndReset: true,
      },
    };
  });

  useRequest(getTicketGroupTypes, {
    onSuccess(data) {
      ticketTypeGroupList.value = data;
    },
  });
  useRequest(getUserList, {
    onSuccess(data) {
      userList.value = data.results.map((item) => ({
        label: item.display_name,
        value: item.username,
      }));
    },
  });

  return tableFilter;
};
