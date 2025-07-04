<template>
  <div>
    <DbCard
      v-if="data.length"
      class="search-result-task search-result-card"
      mode="collapse"
      :title="t('历史任务')">
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
        :pagination="pagination"
        :settings="tableSetting"
        @setting-change="updateTableSettings" />
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

  import TaskFlowModel from '@services/model/taskflow/taskflow';

  import { useLocation, useTableSettings } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: TaskFlowModel[];
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
  const router = useRouter();
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
      field: 'root_id',
      label: 'ID',
      render: ({ data }: { data: TaskFlowModel }) => (
        <bk-button
          theme='primary'
          text
          onclick={() => handleToTask(data)}>
          <TextHighlight
            keyword={props.keyword}
            highLightColor='#FF9C01'
            text={data.root_id}
          />
        </bk-button>
      ),
      width: 160,
    },
    {
      field: 'ticket_type_display',
      filter: {
        list: Array.from(filterMap.value.ticketTypeSet).map((ticketTypeItem) => ({
          text: ticketTypeItem,
          value: ticketTypeItem,
        })),
      },
      label: t('任务类型'),
      render: ({ data }: { data: TaskFlowModel }) => data.ticket_type_display || '--',
      width: 200,
    },
    {
      field: 'status',
      label: t('状态'),
      render: ({ data }: { data: TaskFlowModel }) => (
        <DbStatus
          theme={data.statusTheme}
          type='linear'>
          {t(data.statusText)}
        </DbStatus>
      ),
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
      render: ({ data }: { data: TaskFlowModel }) => filterMap.value.bizNameMap[data.bk_biz_id] || '--',
    },
    {
      field: 'bk_idc_name',
      label: t('关联单据'),
      render: ({ data }: { data: TaskFlowModel }) => (
        <bk-button
          theme='primary'
          text
          onClick={() => handleToTicket(data.uid)}>
          {data.uid}
        </bk-button>
      ),
    },
    {
      field: 'created_by',
      label: t('执行人'),
      render: ({ data }: { data: TaskFlowModel }) => data.created_by || '--',
      sort: true,
    },
    {
      field: 'created_at',
      label: t('执行时间'),
      render: ({ data }: { data: TaskFlowModel }) => data.createAtDisplay,
      sort: true,
    },
    // {
    //   label: t('耗时'),
    //   field: 'bk_idc_name',
    //   render: ({ data }: { data: TaskFlowModel }) => data.bk_idc_name || '--',
    // },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: ['root_id', 'ticket_type_display', 'status', 'bk_biz_id', 'bk_idc_name', 'created_by', 'created_at'],
    fields: (columns.value || [])
      .filter((item) => item.field)
      .map((item) => ({
        disabled: item.field === 'root_id',
        field: item.field as string,
        label: item.label as string,
      })),
  };

  const { settings: tableSetting, updateTableSettings } = useTableSettings(
    UserPersonalSettings.QUICK_SEARCH_TASK,
    defaultSettings,
  );

  const handleToTask = (data: Props['data'][number]) => {
    location(
      {
        name: 'taskHistoryDetail',
        params: {
          root_id: data.root_id,
        },
      },
      data.bk_biz_id,
    );
  };

  const handleToTicket = (id: string) => {
    const url = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: id,
      },
    });
    window.open(url.href, '_blank');
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
