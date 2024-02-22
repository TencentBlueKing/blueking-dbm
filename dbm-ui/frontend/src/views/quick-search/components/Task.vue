<template>
  <DbCard
    class="search-result-task search-result-card"
    mode="collapse"
    :title="t('历史任务')">
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
      :data="data"
      :settings="tableSetting"
      @setting-change="updateTableSettings" />
  </DbCard>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TaskFlowModel from '@services/model/taskflow/taskflow';

  import {
    useLocation,
    useTableSettings,
  } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

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
      filter: {
        list: Array.from(filterMap.value.ticketTypeSet).map(ticketTypeItem => ({
          value: ticketTypeItem,
          text: ticketTypeItem,
        })),
      },
      render: ({ data }: { data: TaskFlowModel }) => data.ticket_type_display || '--',
    },
    {
      label: t('状态'),
      field: 'status',
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
        list: Object.entries(filterMap.value.bizNameMap).reduce((prevList, bizItem) => [...prevList, {
          value: Number(bizItem[0]),
          text: bizItem[1],
        }], [] as {
          value: number,
          text: string
        }[]),
      },
      render: ({ data }: { data: TaskFlowModel }) => filterMap.value.bizNameMap[data.bk_biz_id] || '--',
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
      sort: true,
      render: ({ data }: { data: TaskFlowModel }) => data.created_by || '--',
    },
    {
      label: t('执行时间'),
      field: 'created_at',
      sort: true,
      render: ({ data }: { data: TaskFlowModel }) => data.createAtDisplay,
    },
    // {
    //   label: t('耗时'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TaskFlowModel }) => data.bk_idc_name || '--',
    // },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: item.field === 'root_id',
    })),
    checked: [
      'root_id',
      'ticket_type_display',
      'status',
      'bk_biz_id',
      'bk_idc_name',
      'created_by',
      'created_at',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.QUICK_SEARCH_TASK, defaultSettings);

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
