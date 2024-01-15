<template>
  <DbCard
    class="search-result-ticket search-result-card"
    mode="collapse"
    :title="t('单据')">
    <template #desc>
      {{ t('共n条', { n: data.length }) }}
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

  import DbStatus from '@components/db-status/index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';

  interface Props {
    keyword: string,
    data: TicketModel[],
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const location = useLocation();

  const renderBizNameMap = computed(() => {
    const currentBizNameMap = props.bizIdNameMap;
    return props.data.reduce((prevBizNameMap, dataItem) => {
      if (!prevBizNameMap[dataItem.bk_biz_id]) {
        return Object.assign(prevBizNameMap, {
          [dataItem.bk_biz_id]: currentBizNameMap[dataItem.bk_biz_id],
        });
      }

      return prevBizNameMap;
    }, {} as Props['bizIdNameMap']);
  });

  const columns = computed(() => [
    {
      label: t('单号'),
      field: 'id',
      width: 150,
      render: ({ data }: { data: TicketModel }) => (
        <>
          <bk-button
            text
            theme="primary"
            onclick={() => handleToTicket(data)}>
            <HightLightText
              keyWord={props.keyword}
              text={String(data.id)}
              highLightColor='#FF9C01' />
          </bk-button>
        </>
      ),
    },
    {
      label: t('单据类型'),
      field: 'ticket_type_display',
      render: ({ data }: { data: TicketModel }) => data.ticket_type_display || '--',
    },
    {
      label: t('单据状态'),
      field: 'status',
      render: ({ data }: { data: TicketModel }) => (
        <DbStatus
          type="linear"
          theme={data.tagTheme}>
          {t(data.statusText)}
        </DbStatus>
      ),
    },
    {
      label: t('业务'),
      field: 'bk_biz_id',
      filter: {
        list: Object.entries(renderBizNameMap.value).reduce((prevList, bizItem) => [...prevList, {
          value: Number(bizItem[0]),
          text: bizItem[1],
        }], [] as {
          value: number,
          text: string
        }[]),
      },
      render: ({ data }: { data: TicketModel }) => renderBizNameMap.value[data.bk_biz_id] || '--',
    },
    // {
    //   label: t('耗时'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TicketModel }) => data.bk_idc_name || '--',
    // },
    {
      label: t('申请人'),
      field: 'creator',
      render: ({ data }: { data: TicketModel }) => data.creator || '--',
    },
    {
      label: t('申请时间'),
      field: 'create_at',
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
