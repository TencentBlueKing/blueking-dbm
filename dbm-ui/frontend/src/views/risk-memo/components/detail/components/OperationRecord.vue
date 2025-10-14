<template>
  <PrimaryTable
    class="operation-record-table-mian"
    :data="recordList"
    :loading="listLoading"
    max-height="calc(100vh - 300px)">
    <TableColumn
      col-key="creator"
      :title="t('操作人')">
    </TableColumn>
    <TableColumn
      col-key="create_at"
      :title="t('操作时间')">
      <template #default="{ row }">
        {{ utcDisplayTime(row.create_at) }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="oper_type"
      :title="t('操作类型')">
      <template #default="{ row }">
        {{ operateTypeDisplayNameMap[row.oper_type] || '--' }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRiskOperateRecords } from '@services/source/riskMemo';

  import { utcDisplayTime } from '@utils';

  type OperateRecordList = ServiceReturnType<typeof getRiskOperateRecords>['results'];

  interface Props {
    riskId?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    riskId: undefined,
  });

  const { t } = useI18n();

  const recordList = ref<OperateRecordList>([]);

  const { loading: listLoading, run: runGetRiskMemoList } = useRequest(getRiskOperateRecords, {
    manual: true,
    onSuccess: (data) => {
      recordList.value = data.results;
    },
  });

  const operateTypeDisplayNameMap: Record<string, string> = {
    create_follow_up: t('添加跟进'),
    create_require: t('创建需求'),
    create_risk: t('创建风险'),
    delete_follow_up: t('删除跟进'),
    delete_risk: t('删除风险'),
    final: t('结项'),
    final_require: t('标记为失效'),
    restart_require: t('重启要求'),
    restart_risk: t('重启风险'),
    update_follow_up: t('修改跟进内容'),
    update_require: t('修改要求'),
    update_risk: t('修改风险'),
  };

  watch(
    () => props.riskId,
    () => {
      if (props.riskId) {
        runGetRiskMemoList({ limit: -1, offset: 0, risk: props.riskId });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .operation-record-table-mian {
    .t-table__header th {
      background-color: #f0f1f5;
    }
  }
</style>
