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
  <TableColumn
    col-key="cluster_state"
    :filter="columnFilter"
    :min-width="200"
    :title="t('运行概况')">
    <template #default="{ row }: { row: IRowData }">
      <div class="cluster-state-column-cell">
        <div
          v-for="field in renderFieldList"
          :key="field.key"
          class="cluster-state-column-item">
          <span class="cluster-state-column-label">{{ `${field.name} ： ` }}</span>
          <DbStatus
            v-if="field.key === 'status' && clusterStateStatusThemeMap[String(row.states[field.key]?.value)]"
            :theme="clusterStateStatusThemeMap[String(row.states[field.key]?.value)]">
            {{ getClusterStateDisplay(row.states, field.key) }}
          </DbStatus>
          <span v-else>{{ getClusterStateDisplay(row.states, field.key) }}</span>
        </div>
        <div
          v-if="isOverflow"
          class="cluster-state-column-item">
          <AuthButton
            :action-id="viewActionId"
            :permission="Boolean(_.get(row.permission, viewActionId))"
            :resource="row.id"
            text
            theme="primary"
            @click="(event: MouseEvent) => handleViewAll(row.id, event)">
            {{ t('查看全部n项', { n: displayFields.length }) }}
          </AuthButton>
        </div>
      </div>
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { clusterStateStatusThemeMap, getClusterStateDisplay, useClusterStateSchema } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterState from '@components/db-table/components/ClusterState.vue';

  import { CLUSTER_DETAIL_ANCHOR_CLUSTER_STATE } from '@views/db-manage/common/cluster-details/constants';

  import type { ClusterTypeRelateClusterModel } from './types';

  type IClusterType = ClusterTypes.TENDBCLUSTER | ClusterTypes.TENDBHA | ClusterTypes.TENDBSINGLE;

  type IRowData = ClusterTypeRelateClusterModel[IClusterType];

  interface Props {
    clusterType: IClusterType;
  }

  type Emits = (e: 'go-detail', id: number, event: MouseEvent, detailPanel: string, anchor: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  // 单元格最多展示的行数
  const MAX_ROW_COUNT = 6;

  // 与集群主访问入口（MasterDomainCell）的查看权限保持一致
  const viewActionIdMap: Record<IClusterType, string> = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbcluster_view',
    [ClusterTypes.TENDBHA]: 'mysql_view',
    [ClusterTypes.TENDBSINGLE]: 'mysql_view',
  };

  const { t } = useI18n();

  const { displayFields } = useClusterStateSchema(props.clusterType);

  // 列筛选与搜索栏「运行概况」条件同一个 id，值为逗号分隔的 state__{key}#{value}，由搜索栏拆成 state__{key} 参数
  const columnFilter = {
    component: markRaw(ClusterState),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      clusterType: props.clusterType,
    },
    showConfirmAndReset: true,
  };

  const viewActionId = computed(() => viewActionIdMap[props.clusterType]);
  const isOverflow = computed(() => displayFields.value.length > MAX_ROW_COUNT);
  // 超过上限时留最后一行给「查看全部 N 项」
  const renderFieldList = computed(() =>
    isOverflow.value ? displayFields.value.slice(0, MAX_ROW_COUNT - 1) : displayFields.value,
  );

  const handleViewAll = (id: number, event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    emits('go-detail', id, event, 'info', CLUSTER_DETAIL_ANCHOR_CLUSTER_STATE);
  };
</script>
<style lang="less">
  .cluster-state-column-cell {
    padding: 4px 0;
    line-height: 20px;

    .cluster-state-column-item {
      display: flex;
      align-items: center;
      white-space: nowrap;
    }

    .cluster-state-column-label {
      white-space: pre;
    }
  }
</style>
