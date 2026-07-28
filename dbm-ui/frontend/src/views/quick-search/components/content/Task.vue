<template>
  <div>
    <DbCard
      class="search-result-task search-result-card"
      mode="collapse"
      :title="t('任务')">
      <template #desc>
        <I18nT
          class="ml-8"
          keypath="共n条"
          style="color: #63656e"
          tag="span">
          <template #n>
            <strong>{{ count }}</strong>
          </template>
        </I18nT>
      </template>
      <DbTable
        ref="table"
        class="mt-14"
        :data-source="dataSource"
        row-key="root_id"
        @clear-search="handleClearSearch"
        @request-success="handleReqestSuccess">
        <TableColumn
          col-key="root_id"
          title="ID"
          :width="160">
          <template #default="{ row }: { row: TaskFlowModel }">
            <BkButton
              text
              theme="primary"
              @click="handleToTask(row)">
              <TextHighlight
                high-light-color="#FF9C01"
                :keyword="keyword"
                :text="String(row.root_id)" />
            </BkButton>
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_type_display"
          :title="t('任务类型')"
          :width="200">
          <template #default="{ row }: { row: TaskFlowModel }">
            {{ row.ticket_type_display || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :title="t('状态')">
          <template #default="{ row }: { row: TaskFlowModel }">
            <DbStatus
              :theme="row.statusTheme"
              type="linear">
              {{ t(row.statusText) }}
            </DbStatus>
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_biz_id"
          :title="t('业务')">
          <template #default="{ row }: { row: TaskFlowModel }">
            {{ bizIdNameMap[row.bk_biz_id] || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="uid"
          :title="t('关联单据')">
          <template #default="{ row }: { row: TaskFlowModel }">
            <BkButton
              v-if="row.uid"
              text
              theme="primary"
              @click="handleToTicket(row.uid)">
              {{ row.uid }}
            </BkButton>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="created_by"
          :title="t('执行人')">
          <template #default="{ row }: { row: TaskFlowModel }">
            {{ row.created_by || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="created_at"
          :title="t('执行时间')">
          <template #default="{ row }: { row: TaskFlowModel }">
            {{ row.createAtDisplay || '--' }}
          </template>
        </TableColumn>
      </DbTable>
    </DbCard>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TaskFlowModel from '@services/model/taskflow/taskflow';
  import { quickSearchResult } from '@services/source/quickSearch';

  import { useLocation } from '@hooks';

  import { batchSplitRegex } from '@common/regex';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    formData: {
      bk_biz_ids: number[];
      db_types: string[];
      filter_type: string;
      resource_types: string[];
    };
    keyword: string;
  }

  interface Exposed {
    fetchData: () => void;
  }

  type Emits = (e: 'clear-search') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();
  const location = useLocation();

  const tableRef = useTemplateRef('table');

  const count = ref(0);

  const fetchData = () => {
    if (props.formData.resource_types.length > 0 && !props.formData.resource_types.includes('task')) {
      return;
    }
    tableRef.value?.fetchData();
  };

  // watch(
  //   () => props.keyword,
  //   () => {
  //     fetchData();
  //   },
  // );

  const dataSource = (params: ServiceParameters<typeof quickSearchResult>) => {
    return quickSearchResult({
      ...params,
      ...props.formData,
      keyword: props.keyword.replace(batchSplitRegex, ' '),
      resource_type: 'task',
    });
  };

  const handleReqestSuccess = (data: ServiceReturnType<typeof quickSearchResult>) => {
    count.value = data.count;
  };

  const handleToTask = (data: TaskFlowModel) => {
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

  const handleClearSearch = () => {
    emits('clear-search');
  };

  // onMounted(() => {
  //   fetchData();
  // });

  onActivated(() => {
    fetchData();
  });

  defineExpose<Exposed>({
    fetchData,
  });
</script>

<style lang="less" scoped>
  @import './table-card.less';
</style>
