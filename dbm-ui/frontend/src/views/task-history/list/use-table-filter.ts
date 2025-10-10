import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import TaskFlowModel from '@services/model/taskflow/taskflow';
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
      bk_biz_id__in: {
        component: markRaw(MultipleSelect),
        name: t('业务'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        props: {
          list: globalBizsStore.bizs.map((item) => ({
            label: item.name,
            value: `${item.bk_biz_id}`,
          })),
        },
        showConfirmAndReset: true,
      },
      created_at: {
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
      created_by__in: {
        component: markRaw(MultipleSelect),
        name: t('执行人'),
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
      root_id__in: {
        component: markRaw(MultipleInput),
        name: t('单号'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        showConfirmAndReset: true,
      },
      status__in: {
        component: markRaw(MultipleSelect),
        name: t('状态'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        props: {
          list: Object.keys(TaskFlowModel.STATUS_TEXT_MAP).map((value: string) => ({
            label: t(TaskFlowModel.STATUS_TEXT_MAP[value]),
            value,
          })),
        },
        showConfirmAndReset: true,
      },
      ticket_type__in: {
        component: markRaw(MultCascader),
        name: t('任务类型'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        props: {
          list: ticketTypeGroupList.value,
        },
        showConfirmAndReset: true,
      },
      uid__in: {
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

  useRequest(getTicketGroupTypes, {
    onSuccess(data) {
      ticketTypeGroupList.value = data;
    },
  });

  return tableFilter;
};
