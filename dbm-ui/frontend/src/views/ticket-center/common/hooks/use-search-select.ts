import dayjs from 'dayjs';
import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketGroupTypes } from '@services/source/ticket';

import { useGlobalBizs } from '@stores';

import { makeMap } from '@utils';

const quickSearchValue = ref<Record<string, any>>({});

export default (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const quickSearchData = computed(() => {
    const serachList = [
      {
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
        id: 'cluster',
        name: t('集群'),
      },
      {
        id: 'bk_biz_id',
        list: globalBizsStore.bizs.map((item) => ({
          label: item.name,
          value: `${item.bk_biz_id}`,
        })),
        name: t('业务'),
        type: 'single',
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
        name: t('提单人'),
      },
      {
        id: 'create_at',
        name: t('申请时间'),
        props: {
          presets: {
            [t('今天')]: [dayjs().toDate(), dayjs().toDate()],
            [t('近 15 天')]: [dayjs().subtract(14, 'day').toDate(), dayjs().toDate()],
            [t('近 30 天')]: [dayjs().subtract(29, 'day').toDate(), dayjs().toDate()],
            [t('近 7 天')]: [dayjs().subtract(6, 'day').toDate(), dayjs().toDate()],
          },
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
