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
  <div class="render-data">
    <RenderTable>
      <template
        #default="slotProps">
        <RenderTableHeadColumn
          :min-width="215"
          :row-width="slotProps.rowWidth"
          :width="225">
          {{ $t('源实例') }}
          <template #append>
            <span
              class="batch-edit-btn"
              @click="handleShowBatchSelectCluster">
              <DbIcon type="batch-host-select" />
            </span>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="280"
          :row-width="slotProps.rowWidth"
          :width="300">
          {{ $t('所属集群') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="320"
          :row-width="slotProps.rowWidth"
          :width="350">
          {{ $t('模块') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="260"
          :row-width="slotProps.rowWidth"
          :width="280">
          {{ $t('新实例') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-fixed="slotProps.isOverflow"
          :min-width="100"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="170">
          {{ $t('操作') }}
        </RenderTableHeadColumn>
      </template>

      <template #data="slotProps">
        <slot :is-overflow="slotProps.isOverflow" />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import RenderTableHeadColumn from '@views/spider-manage/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/spider-manage/common/render-table/Index.vue';

  interface Emits{
    (e: 'batchSelectCluster'): void,
  }

  const emits = defineEmits<Emits>();

  const handleShowBatchSelectCluster = () => {
    emits('batchSelectCluster');
  };
</script>
<style lang="less">
  .render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
