<template>
  <div class="operate-history-main">
    <BkLoading
      class="operation-history-table"
      :loading="loading"
      :z-index="2">
      <PrimaryTable
        :data="tableData"
        height="100%"
        row-key="id">
        <TableColumn
          col-key="node_name"
          fixed="left"
          :min-width="300"
          :title="t('节点名称')">
          <template #default="{ row: data }: { row: RowData }">
            <span>{{ data.node_name || '--' }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="operate_type"
          :min-width="150"
          :title="t('操作类型')">
          <template #default="{ row: data }: { row: RowData }">
            <BkTag
              v-if="data.operate_type === 'skip'"
              style="background: #fafbfd"
              type="stroke">
              {{ t('跳过') }}
            </BkTag>
            <BkTag
              v-else-if="data.operate_type === 'retry'"
              theme="info"
              type="stroke">
              {{ t('重试') }}
            </BkTag>
            <BkTag
              v-else-if="data.operate_type === 'force_fail'"
              theme="danger"
              type="stroke">
              {{ t('强制失败') }}
            </BkTag>
            <BkTag
              v-else-if="data.operate_type === 'pipeline_terminate'"
              theme="danger"
              type="stroke">
              {{ t('终止任务') }}
            </BkTag>
            <BkTag
              v-else-if="data.operate_type === 'force_retry'"
              theme="warning"
              type="stroke">
              {{ t('强制重试') }}
            </BkTag>
            <BkTag
              v-else-if="data.operate_type === 'force_skip'"
              theme="warning"
              type="stroke">
              {{ t('强制跳过') }}
            </BkTag>
            <BkTag
              v-else
              theme="warning"
              type="stroke">
              {{ t('确认执行') }}
            </BkTag>
          </template>
        </TableColumn>
        <TableColumn
          col-key="operator"
          :min-width="120"
          :title="t('操作人')" />
        <TableColumn
          col-key="operate_date"
          :min-width="120"
          :title="t('操作时间')">
          <template #default="{ row: data }: { row: RowData }">
            <span>{{ utcDisplayTime(data.operate_date) }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="remark"
          :min-width="120"
          :title="t('操作原因')">
          <template #default="{ row: data }: { row: RowData }">
            <span>{{ data.remark || '--' }}</span>
          </template>
        </TableColumn>
        <template #empty>
          <EmptyStatus
            :is-anomalies="isAnomalies"
            :is-searching="false"
            @refresh="updateTableData" />
        </template>
      </PrimaryTable>
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getNodeOperateRecord } from '@services/source/taskflow';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    rootId: string;
  }

  interface Exposes {
    updateTableData: () => void;
  }

  type RowData = ServiceReturnType<typeof getNodeOperateRecord>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const loading = ref(false);
  const isAnomalies = ref(false);
  const tableData = shallowRef<RowData[]>([]);

  const updateTableData = () => {
    loading.value = true;
    isAnomalies.value = false;
    getNodeOperateRecord({
      root_id: props.rootId,
    })
      .then((data) => {
        tableData.value = data.results;
      })
      .catch(() => {
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        loading.value = false;
      });
  };

  onMounted(() => {
    updateTableData();
  });

  defineExpose<Exposes>({
    updateTableData,
  });
</script>
<style lang="less">
  .operate-history-main {
    height: 100%;
    padding: 16px 25px;
    overflow: hidden;

    .operation-history-table {
      height: 100%;
      overflow: hidden;

      & > div {
        height: 100%;
      }
    }
  }
</style>
