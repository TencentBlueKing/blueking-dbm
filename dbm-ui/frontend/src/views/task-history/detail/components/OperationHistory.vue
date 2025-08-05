<template>
  <div class="operate-history-main">
    <DbTable
      ref="tableRef"
      :data-source="getNodeOperateRecord"
      :pagination="false">
      <BkTableColumn
        field="node_name"
        fixed="left"
        :label="t('节点名称')"
        :min-width="300" />
      <BkTableColumn
        field="operate_type"
        :label="t('操作类型')"
        :min-width="150">
        <template #default="{ data }: { data: RowData }">
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
            v-else
            theme="warning"
            type="stroke">
            {{ t('确认执行') }}
          </BkTag>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="operator"
        :label="t('操作人')"
        :min-width="120" />
      <BkTableColumn
        field="operate_date"
        :label="t('操作时间')"
        :min-width="120">
        <template #default="{ data }: { data: RowData }">
          <span>{{ utcDisplayTime(data.operate_date) }}</span>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getNodeOperateRecord } from '@services/source/taskflow';

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

  const tableRef = ref();

  const updateTableData = () => {
    tableRef.value?.fetchData(
      {},
      {
        root_id: props.rootId,
      },
    );
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
    padding: 16px 25px;
  }
</style>
