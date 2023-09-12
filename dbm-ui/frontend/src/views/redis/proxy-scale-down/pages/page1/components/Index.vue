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
          :min-width="150"
          :row-width="slotProps.rowWidth"
          :width="450">
          <span>{{ $t('目标集群') }}</span>
          <template #append>
            <BkPopover
              :content="$t('批量添加')"
              theme="dark">
              <span
                class="batch-edit-btn"
                @click="handleShowMasterBatchSelector">
                <DbIcon type="batch-host-select" />
              </span>
            </BkPopover>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="150"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="150">
          <span>{{ $t('缩容节点类型') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="150"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="240">
          <span>{{ $t('当前规格') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :row-width="slotProps.rowWidth"
          :width="300">
          <span>{{ $t('缩容至(台)') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="200">
          <span>{{ $t('切换模式') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-fixed="slotProps.isOverflow"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="120">
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
  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/redis/common/render-table/Index.vue';

  interface Emits{
    (e: 'showMasterBatchSelector'): void
  }

  const emits = defineEmits<Emits>();

  const handleShowMasterBatchSelector = () => {
    emits('showMasterBatchSelector');
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
