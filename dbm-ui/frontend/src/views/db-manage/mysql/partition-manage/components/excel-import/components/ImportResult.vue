<!--
 * 导入策略 - 结果展示
 * 全部成功 / 部分成功 / 全部失败
-->

<template>
  <div class="import-result-wrap">
    <!-- 结果图标 + 文案 -->
    <div class="import-result">
      <div
        class="result-icon"
        :class="iconClass">
        <DbIcon :type="iconType" />
      </div>
      <div class="result-title">{{ title }}</div>
      <div class="result-desc">{{ desc }}</div>
    </div>

    <!-- 失败详情表格 -->
    <PrimaryTable
      v-if="data.failed_items.length > 0"
      class="error-table"
      :data="data.failed_items"
      :max-height="200"
      row-key="row">
      <TableColumn
        col-key="row"
        :title="t('行号')"
        :width="60" />
      <TableColumn
        col-key="cluster"
        ellipsis
        :title="t('集群')">
        <template #default="{ row }">
          {{ row.cluster || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="dblikes"
        :title="t('DB名')">
        <template #default="{ row }">
          {{ row.dblikes || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="tblikes"
        :title="t('表名')">
        <template #default="{ row }">
          {{ row.tblikes || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="error"
        :title="t('失败原因')">
        <template #default="{ row }">
          <span class="error-reason">{{ row.error || '--' }}</span>
        </template>
      </TableColumn>
    </PrimaryTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { PrimaryTable } from '@blueking/tdesign-ui';

  import { importFromExcel } from '@services/source/partitionManage';

  type ResultType = 'allFail' | 'partial' | 'success';

  interface Props {
    data: ServiceReturnType<typeof importFromExcel>;
    type: ResultType;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const iconClass = computed(() => ({
    'is-error': props.type === 'allFail',
    'is-success': props.type === 'success',
    'is-warning': props.type === 'partial',
  }));

  const iconType = computed(() => {
    if (props.type === 'success') return 'check-line';
    if (props.type === 'partial') return 'alert';
    return 'close';
  });

  const title = computed(() => {
    if (props.type === 'success') return t('导入成功');
    if (props.type === 'partial') return t('导入完成');
    return t('导入失败');
  });

  const desc = computed(() => {
    if (props.type === 'success') {
      return t('共 n 条策略，全部导入成功', { n: props.data.success_count });
    }
    if (props.type === 'partial') {
      return t('成功 n 条，失败 m 条', { m: props.data.failed_count, n: props.data.success_count });
    }
    return t('共 n 条策略，全部校验不通过', { n: props.data.failed_count });
  });
</script>

<style lang="less" scoped>
  .import-result {
    padding: 8px 0;
    text-align: center;
  }

  .result-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    margin: 0 auto 12px;
    font-size: 24px;
    border-radius: 50%;

    &.is-success {
      color: #2dcb56;
      background: #e5f6ea;
    }

    &.is-warning {
      color: #ff9c01;
      background: #fff3e1;
    }

    &.is-error {
      color: #ea3636;
      background: #feecec;
    }
  }

  .result-title {
    margin-bottom: 4px;
    font-size: 14px;
    font-weight: 500;
    color: #313238;
  }

  .result-desc {
    margin-bottom: 16px;
    font-size: 12px;
    color: #979ba5;
  }

  .error-reason {
    color: #ea3636;
  }
</style>
