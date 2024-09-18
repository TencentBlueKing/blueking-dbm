import { computed, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import TicketModel from '@services/model/ticket/ticket';
import { getTicketTypes } from '@services/source/ticket';

import type { SearchValue } from '@components/vue2/search-select/index.vue';

import { getSearchSelectorParams } from '@utils';

const value = ref<SearchValue[]>([]);

export default () => {
  const { t } = useI18n();

  const ticketTypeList = shallowRef<{ id: string; name: string }[]>([]);

  const searchSelectData = computed(() => [
    {
      name: t('单号'),
      id: 'id',
    },
    {
      name: t('单据类型'),
      id: 'ticket_type__in',
      multiple: true,
      children: ticketTypeList.value,
    },
    {
      name: t('集群'),
      id: 'cluster',
      multiple: true,
    },
    {
      name: t('状态'),
      id: 'status__in',
      multiple: true,
      children: Object.keys(TicketModel.statusTextMap).reduce<Record<'id' | 'name', string>[]>((acc, key) => {
        acc.push({
          id: key,
          name: t(TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap]),
        });
        return acc;
      }, []),
    },
    {
      name: t('备注'),
      id: 'remark',
    },
  ]);

  const formatSearchValue = computed(() => getSearchSelectorParams(value.value));

  useRequest(getTicketTypes, {
    onSuccess(data) {
      ticketTypeList.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  return {
    value,
    searchSelectData,
    formatSearchValue,
  };
};
