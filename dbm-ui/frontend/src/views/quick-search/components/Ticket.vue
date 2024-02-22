<template>
  <DbCard
    class="search-result-ticket search-result-card"
    mode="collapse"
    :title="t('单据')">
    <template #desc>
      <I18nT
        class="ml-8"
        keypath="共n条"
        style="color: #63656E;"
        tag="span">
        <template #n>
          <strong>{{ data.length }}</strong>
        </template>
      </I18nT>
    </template>
    <DbOriginalTable
      class="mt-14 mb-8"
      :columns="columns"
      :data="data" />
  </DbCard>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { useLocation } from '@hooks';

  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';

  interface Props {
    keyword: string,
    data: TicketModel[],
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const location = useLocation();

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
      label: t('单号'),
      field: 'id',
      width: 150,
      render: ({ data }: { data: TicketModel }) => (
        <bk-button
          text
          theme="primary"
          onclick={() => handleToTicket(data)}>
          <HightLightText
            keyWord={props.keyword}
            text={String(data.id)}
            highLightColor='#FF9C01' />
        </bk-button>
      ),
    },
    {
      label: t('单据类型'),
      field: 'ticket_type_display',
      filter: {
        list: Array.from(filterMap.value.ticketTypeSet).map(ticketTypeItem => ({
          value: ticketTypeItem,
          text: ticketTypeItem,
        })),
      },
      render: ({ data }: { data: TicketModel }) => data.ticket_type_display || '--',
    },
    {
      label: t('单据状态'),
      field: 'status',
      sort: true,
      render: ({ data }: { data: TicketModel }) => (
        <bk-tag theme={data.tagTheme}>
          {t(data.statusText)}
        </bk-tag>
      ),
    },
    {
      label: t('业务'),
      field: 'bk_biz_id',
      filter: {
        list: Object.entries(filterMap.value.bizNameMap).reduce((prevList, bizItem) => [...prevList, {
          value: Number(bizItem[0]),
          text: bizItem[1],
        }], [] as {
          value: number,
          text: string
        }[]),
      },
      render: ({ data }: { data: TicketModel }) => filterMap.value.bizNameMap[data.bk_biz_id] || '--',
    },
    // {
    //   label: t('耗时'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TicketModel }) => data.bk_idc_name || '--',
    // },
    {
      label: t('申请人'),
      field: 'creator',
      sort: true,
      render: ({ data }: { data: TicketModel }) => data.creator || '--',
    },
    {
      label: t('申请时间'),
      field: 'create_at',
      sort: true,
      render: ({ data }: { data: TicketModel }) => data.createAtDisplay || '--',
    },
  ]);

  const handleToTicket = (data: Props['data'][number]) => {
    location({
      name: 'bizTicketManage',
      query: {
        id: data.id,
      },
    }, data.bk_biz_id);
  };
</script>

<style lang="less" scoped>
@import "../style/table-card.less";
</style>
