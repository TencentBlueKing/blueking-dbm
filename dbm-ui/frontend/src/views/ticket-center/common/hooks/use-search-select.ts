import dayjs from 'dayjs';
import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketGroupTypes } from '@services/source/ticket';
import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { makeMap } from '@utils';

const quickSearchValue = ref<Record<string, any>>({});

export default (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const fetchUserList = (params: { defaultValue?: string; keyword?: string }) => {
    const requestParams = {};
    if (params.defaultValue) {
      Object.assign(requestParams, { exact_lookups: params.defaultValue });
    }
    if (params.keyword) {
      Object.assign(requestParams, { fuzzy_lookups: params.keyword });
    }

    return getUserList(requestParams).then((data) =>
      data.results.map((item) => ({
        label: `${item.display_name}(${item.username})`,
        value: item.username,
      })),
    );
  };

  const quickSearchData = computed(() => {
    const serachList = [
      {
        description: t('支持输入多个'),
        id: 'ids',
        name: t('单号'),
      },
      {
        id: 'ticket_type__in',
        name: t('单据类型'),
        remoteMethod: () => getTicketGroupTypes(),
        type: 'multiple-cascader',
      },
      {
        description: t('支持输入多个'),
        id: 'cluster',
        name: t('集群'),
      },
      {
        id: 'bk_biz_ids',
        list: globalBizsStore.bizs.map((item) => ({
          label: item.name,
          value: `${item.bk_biz_id}`,
        })),
        name: t('业务'),
        type: 'multiple',
      },
      {
        id: 'status',
        list: Object.keys(TicketModel.statusTextMap).reduce<Record<'label' | 'value', string>[]>((acc, key) => {
          acc.push({
            label: TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap],
            value: key,
          });
          return acc;
        }, []),
        name: t('单据状态'),
        type: 'multiple',
      },
      {
        id: 'remark',
        name: t('备注'),
      },
      {
        id: 'creator',
        name: t('申请人'),
        remoteMethod: (params: Parameters<typeof fetchUserList>[0]) => fetchUserList(params),
        remoteSearch: true,
        type: 'multiple',
      },
      {
        id: 'create_at',
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
        type: 'datetime-range',
      },
    ];

    if (!options.exclude) {
      return serachList;
    }

    const excludeMap = makeMap(options.exclude);
    return serachList.filter((item) => !excludeMap[item.id]);
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });

  return {
    quickSearchData,
    quickSearchValue,
  };
};
