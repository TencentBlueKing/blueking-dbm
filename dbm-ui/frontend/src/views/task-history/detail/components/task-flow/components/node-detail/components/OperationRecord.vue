<template>
  <div class="operate-history-main">
    <DbTable
      ref="tableRef"
      :data-source="getNodeOperateRecord"
      :pagination="false">
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
          {{ utcDisplayTime(data.operate_date) }}
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
    nodeId?: string;
    rootId: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    nodeId: '',
  });

  type RowData = ServiceReturnType<typeof getNodeOperateRecord>['results'][number];

  const { t } = useI18n();

  const tableRef = ref();

  watch(
    () => props.nodeId,
    () => {
      if (props.nodeId) {
        setTimeout(() => {
          tableRef.value?.fetchData(
            {},
            {
              node_id: props.nodeId,
              root_id: props.rootId,
            },
          );
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .operate-history-main {
    padding: 0 16px;
  }
</style>
