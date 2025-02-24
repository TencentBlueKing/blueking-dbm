import { computed, onBeforeUnmount, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketTypes } from '@services/source/ticket';

import { useGlobalBizs } from '@stores';

import type { SearchValue } from '@components/vue2/search-select/index.vue';

import { getSearchSelectorParams, makeMap } from '@utils';

const value = ref<SearchValue[]>([]);

const ticketTypeList = shallowRef<{ id: string; name: string }[]>([]);

const create = (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const searchSelectData = computed(() => {
    const serachList = [
      {
        id: 'ids',
        multiple: true,
        name: t('单号'),
      },
      {
        children: ticketTypeList.value,
        id: 'ticket_type__in',
        multiple: true,
        name: t('单据类型'),
      },
      {
        id: 'cluster',
        name: t('集群'),
      },
      {
        children: globalBizsStore.bizs.map((item) => ({
          id: `${item.bk_biz_id}`,
          name: item.name,
        })),
        id: 'bk_biz_id',
        name: t('业务'),
      },
      {
        children: Object.keys(TicketModel.statusTextMap).reduce<Record<'id' | 'name', string>[]>((acc, key) => {
          acc.push({
            id: key,
            name: TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap],
          });
          return acc;
        }, []),
        id: 'status',
        multiple: true,
        name: t('单据状态'),
      },
      {
        id: 'remark',
        name: t('备注'),
      },
      {
        id: 'creator',
        name: t('提单人'),
      },
    ];

    if (!options.exclude) {
      return serachList;
    }

    const excludeMap = makeMap(options.exclude);
    return serachList.filter((item) => !excludeMap[item.id]);
  });

  const formatSearchValue = computed(() => getSearchSelectorParams(value.value));

  const searchFieldMap = computed(() =>
    searchSelectData.value.reduce<Record<string, { label: string; value: string }[]>>((result, item) => {
      if (item.children) {
        Object.assign(result, {
          [item.id]: item.children.map((childItem) => ({
            label: childItem.name,
            value: childItem.id,
          })),
        });
      }
      return result;
    }, {}),
  );

  useRequest(getTicketTypes, {
    cacheKey: 'ticketTypes',
    onSuccess(data) {
      ticketTypeList.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));
    },
    staleTime: 24 * 60 * 60 * 1000,
  });

  return {
    formatSearchValue,
    searchFieldMap,
    searchSelectData,
    ticketTypeList,
    value,
  };
};

let context: ReturnType<typeof create> | undefined;

export default (...args: Parameters<typeof create>) => {
  if (!context) {
    context = create(...args);
  }

  onBeforeUnmount(() => {
    context = undefined;
  });

  return context;
};
