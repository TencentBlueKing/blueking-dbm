<template>
  <div>
    <DbCard
      v-if="data.length"
      class="search-result-ticket search-result-card"
      mode="collapse"
      :title="t('单据')">
      <template #desc>
        <I18nT
          class="ml-8"
          keypath="共n条"
          style="color: #63656e"
          tag="span">
          <template #n>
            <strong>{{ data.length }}</strong>
          </template>
        </I18nT>
      </template>
      <DbOriginalTable
        class="mt-14 mb-8"
        :columns="columns"
        :data="data"
        :pagination="pagination" />
    </DbCard>
    <EmptyStatus
      v-else
      class="empty-status"
      :is-anomalies="isAnomalies"
      :is-searching="isSearching"
      @clear-search="handleClearSearch"
      @refresh="handleRefresh" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { useLocation } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: TicketModel[];
    isAnomalies: boolean;
    isSearching: boolean;
    keyword: string;
  }

  interface Emits {
    (e: 'refresh'): void;
    (e: 'clearSearch'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const location = useLocation();

  const pagination = ref({
    count: props.data.length,
    limit: 10,
  });

  const filterMap = computed(() => {
    const currentBizNameMap = props.bizIdNameMap;
    const bizNameMap: Props['bizIdNameMap'] = {};
    const ticketTypeSet = new Set<string>();

    props.data.forEach((dataItem) => {
      if (!bizNameMap[dataItem.bk_biz_id]) {
        bizNameMap[dataItem.bk_biz_id] = currentBizNameMap[dataItem.bk_biz_id];
      }

      ticketTypeSet.add(dataItem.ticket_type_display);
    });

    return {
      bizNameMap,
      ticketTypeSet,
    };
  });

  const columns = computed(() => [
    {
      field: 'id',
      label: t('单号'),
      render: ({ data }: { data: TicketModel }) => (
        <bk-button
          theme='primary'
          text
          onclick={() => handleToTicket(data)}>
          <TextHighlight
            keyword={props.keyword}
            highLightColor='#FF9C01'
            text={String(data.id)}
          />
        </bk-button>
      ),
      width: 150,
    },
    {
      field: 'ticket_type_display',
      filter: {
        list: Array.from(filterMap.value.ticketTypeSet).map((ticketTypeItem) => ({
          text: ticketTypeItem,
          value: ticketTypeItem,
        })),
      },
      label: t('单据类型'),
      render: ({ data }: { data: TicketModel }) => data.ticket_type_display || '--',
    },
    {
      field: 'status',
      label: t('单据状态'),
      render: ({ data }: { data: TicketModel }) => <TicketStatusTag data={data} />,
      sort: true,
    },
    {
      field: 'bk_biz_id',
      filter: {
        list: Object.entries(filterMap.value.bizNameMap).map((bizItem) => ({
          text: bizItem[1],
          value: Number(bizItem[0]),
        })),
      },
      label: t('业务'),
      render: ({ data }: { data: TicketModel }) => filterMap.value.bizNameMap[data.bk_biz_id] || '--',
    },
    // {
    //   label: t('耗时'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TicketModel }) => data.bk_idc_name || '--',
    // },
    {
      field: 'creator',
      label: t('申请人'),
      render: ({ data }: { data: TicketModel }) => data.creator || '--',
      sort: true,
    },
    {
      field: 'create_at',
      label: t('申请时间'),
      render: ({ data }: { data: TicketModel }) => data.createAtDisplay || '--',
      sort: true,
    },
  ]);

  const handleToTicket = (data: Props['data'][number]) => {
    location(
      {
        name: 'bizTicketManage',
        params: {
          ticketId: data.id,
        },
      },
      data.bk_biz_id,
    );
  };

  const handleRefresh = () => {
    emits('refresh');
  };

  const handleClearSearch = () => {
    emits('clearSearch');
  };
</script>

<style lang="less" scoped>
  @import '../style/table-card.less';
</style>
