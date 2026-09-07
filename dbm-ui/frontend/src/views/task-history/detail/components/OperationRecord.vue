<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    class="operate-record-main"
    :class="{ 'is-node-scope': isNodeScope }">
    <BkLoading
      class="operate-record-table"
      :loading="loading"
      :z-index="2">
      <PrimaryTable
        :data="tableData"
        height="100%"
        row-key="id">
        <TableColumn
          v-if="!isNodeScope"
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
              :style="getOperateTag(data.operate_type).style"
              :theme="getOperateTag(data.operate_type).theme"
              type="stroke">
              {{ getOperateTag(data.operate_type).text }}
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
    /**
     * 单节点模式：只查该节点的记录，并且不显示节点名称列。
     * 不传表示查整条流程；传空串表示节点还没确定，此时不发请求
     */
    nodeId?: string;
    rootId: string;
  }

  interface Exposes {
    updateTableData: () => void;
  }

  type RowData = ServiceReturnType<typeof getNodeOperateRecord>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const OPERATE_TYPE_TAG_MAP: Record<
    string,
    {
      style?: Record<string, string>;
      text: string;
      theme?: 'danger' | 'info' | 'warning';
    }
  > = {
    force_fail: { text: t('强制失败'), theme: 'danger' },
    force_retry: { text: t('强制重试'), theme: 'warning' },
    force_skip: { text: t('强制跳过'), theme: 'warning' },
    pipeline_terminate: { text: t('终止任务'), theme: 'danger' },
    retry: { text: t('重试'), theme: 'info' },
    skip: { style: { background: '#fafbfd' }, text: t('跳过') },
  };

  const loading = ref(false);
  const isAnomalies = ref(false);
  const tableData = shallowRef<RowData[]>([]);

  const isNodeScope = computed(() => props.nodeId !== undefined);

  // 剩下的都是待继续节点的人工确认
  const getOperateTag = (type: string) => OPERATE_TYPE_TAG_MAP[type] ?? { text: t('确认继续'), theme: 'warning' };

  const updateTableData = () => {
    loading.value = true;
    isAnomalies.value = false;
    getNodeOperateRecord({
      node_id: props.nodeId,
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

  watch(
    () => [props.rootId, props.nodeId],
    () => {
      if (isNodeScope.value && !props.nodeId) {
        return;
      }
      updateTableData();
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    updateTableData,
  });
</script>
<style lang="less">
  .operate-record-main {
    height: 100%;
    padding: 16px 25px;
    overflow: hidden;

    // 侧滑里嵌的表格四周留白更紧
    &.is-node-scope {
      padding: 0 16px;
    }

    .operate-record-table {
      height: 100%;
      overflow: hidden;

      & > div {
        height: 100%;
      }
    }
  }
</style>
