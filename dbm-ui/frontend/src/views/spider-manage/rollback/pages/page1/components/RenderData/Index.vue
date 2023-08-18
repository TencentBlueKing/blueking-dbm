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
          :min-width="180"
          :row-width="slotProps.rowWidth"
          :width="190">
          {{ $t('待构造集群') }}
          <template #append>
            <span
              class="batch-edit-btn"
              @click="handleShowBatchSelector">
              <DbIcon type="batch-host-select" />
            </span>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="300"
          :row-width="slotProps.rowWidth"
          :width="320">
          {{ $t('回档类型') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="110"
          :row-width="slotProps.rowWidth"
          :width="120">
          {{ $t('构造 DB 名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="110"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="120">
          {{ $t('忽略DB名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="110"
          :row-width="slotProps.rowWidth"
          :width="120">
          {{ $t('构造表名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="110"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="120">
          {{ $t('忽略表名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-fixed="slotProps.isOverflow"
          :min-width="80"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="90">
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
    (e: 'batchSelectCluster'): void
  }

  const emits = defineEmits<Emits>();

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };
</script>
<style lang="less">
  .render-data {
    display: block;

    .batch-edit-btn {
      display: inline-block;
      margin-left: 4px;
      line-height: 40px;
      color: #3a84ff;
      vertical-align: top;
      cursor: pointer;
    }
  }
</style>
