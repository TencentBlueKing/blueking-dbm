<template>
  <DbCard
    class="search-result-task search-result-card"
    mode="collapse"
    :title="t('历史任务')">
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

  import TaskFlowModel from '@services/model/taskflow/taskflow';

  import { useLocation } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';

  interface Props {
    keyword: string,
    data: TaskFlowModel[]
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
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
      label: 'ID',
      field: 'root_id',
      width: 160,
      render: ({ data }: { data: TaskFlowModel }) => (
        <bk-button
          text
          theme="primary"
          onclick={() => handleToTask(data)}>
          <HightLightText
            keyWord={props.keyword}
            text={data.root_id}
            highLightColor='#FF9C01' />
        </bk-button>
      ),
    },
    {
      label: t('任务类型'),
      field: 'ticket_type_display',
      width: 200,
      render: ({ data }: { data: TaskFlowModel }) => data.ticket_type_display || '--',
    },
    {
      label: t('状态'),
      field: 'bk_idc_name',
      render: ({ data }: { data: TaskFlowModel }) => (
        <DbStatus
          type="linear"
          theme={data.statusTheme}>
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
      render: ({ data }: { data: TaskFlowModel }) => renderBizNameMap.value[data.bk_biz_id] || '--',
    },
    {
      label: t('关联单据'),
      field: 'bk_idc_name',
      render: ({ data }: { data: TaskFlowModel }) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleToTicket(data.uid)}>
          { data.uid }
        </bk-button>
      ),
    },
    {
      label: t('执行人'),
      field: 'created_by',
      render: ({ data }: { data: TaskFlowModel }) => data.created_by || '--',
    },
    // {
    //   label: t('执行时间'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TaskFlowModel }) => data.bk_idc_name || '--',
    // },
    // {
    //   label: t('耗时'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TaskFlowModel }) => data.bk_idc_name || '--',
    // },
  ]);

  const handleToTask = (data: Props['data'][number]) => {
    location({
      name: 'taskHistoryDetail',
      params: {
        root_id: data.root_id,
      },
    }, data.bk_biz_id);
  };

  const handleToTicket = (id: string) => {
    const url = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id,
      },
    });
    window.open(url.href, '_blank');
  };
</script>

<style lang="less" scoped>
@import "../style/table-card.less";
</style>
