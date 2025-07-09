import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketGroupTypes } from '@services/source/ticket';

import { useGlobalBizs } from '@stores';

import MultCascader from '@components/db-table/components/MultCascader.vue';

import DatetimeRange from '@/components/db-table/components/DatetimeRange.vue';

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

  const tableFilter = computed<ITableFilter>(() => {
    return {
      bk_biz_id: {
        list: globalBizsStore.bizs.map((item) => ({
          label: item.name,
          value: `${item.bk_biz_id}`,
        })),
        name: t('业务'),
        type: 'single',
      },
      create_at: {
        component: markRaw(DatetimeRange),
        name: t('申请时间'),
        props: {
          presets: {
            [t('今天')]: [dayjs().toDate(), dayjs().toDate()],
            [t('近 15 天')]: [dayjs().subtract(14, 'day').toDate(), dayjs().toDate()],
            [t('近 30 天')]: [dayjs().subtract(29, 'day').toDate(), dayjs().toDate()],
            [t('近 7 天')]: [dayjs().subtract(6, 'day').toDate(), dayjs().toDate()],
          },
        },
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

  return tableFilter;
};
