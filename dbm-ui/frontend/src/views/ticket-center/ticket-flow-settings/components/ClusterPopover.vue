<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <span class="cluster-popover">
    <span class="cluster-name">{{ displayName }}</span>
    <BkPopover
      v-if="clusterCount > 1"
      placement="top"
      theme="light"
      trigger="click"
      width="300">
      <span class="cluster-more">共 {{ clusterCount }} 个</span>
      <template #content>
        <div class="cluster-list">
          <div
            v-for="cluster in clusters"
            :key="cluster.cluster_id"
            class="cluster-item">
            {{ cluster.immute_domain }}
          </div>
        </div>
      </template>
    </BkPopover>
  </span>
</template>

<script setup lang="ts">
  interface Cluster {
    cluster_id: number;
    immute_domain: string;
  }

  interface Props {
    clusters: Cluster[];
  }

  const props = defineProps<Props>();

  const displayName = computed(() => props.clusters.map((item) => item.immute_domain).join(','));
  const clusterCount = computed(() => props.clusters.length);
</script>

<style lang="less" scoped>
  .cluster-popover {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
    overflow: hidden;

    .cluster-name {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .cluster-more {
      flex-shrink: 0;
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
      white-space: nowrap;
    }
  }

  .cluster-list {
    max-height: 200px;
    overflow-y: auto;

    .cluster-item {
      padding: 4px 8px;
      line-height: 20px;
      font-size: 12px;

      &::before {
        content: '';
        display: inline-block;
        width: 6px;
        height: 6px;
        margin-right: 8px;
        border-radius: 50%;
        background: #c4c6cc;
        vertical-align: middle;
      }
    }
  }
</style>
