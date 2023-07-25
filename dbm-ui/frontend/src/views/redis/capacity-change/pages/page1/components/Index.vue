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
    <RenderTable
      @row-width-change="handleRowWidthChange"
      @scroll-display="handleScrollDisplay">
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="150"
        :row-width="rowWidth"
        :width="300">
        <span>{{ $t('目标集群') }}</span>
        <template #append>
          <BkPopover
            content="批量添加"
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
        :is-minimum="isMinimum"
        :min-width="150"
        :required="false"
        :row-width="rowWidth"
        :width="200">
        <span>{{ $t('当前资源规格') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="100"
        :required="false"
        :row-width="rowWidth"
        :width="150">
        <span>{{ $t('集群分片数') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="110"
        :required="false"
        :row-width="rowWidth"
        :width="180">
        <span>{{ $t('部署机器组数') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="230"
        :required="false"
        :row-width="rowWidth"
        :width="250">
        <span>{{ $t('当前容量') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="320"
        :row-width="rowWidth"
        :width="350">
        <span>{{ $t('目标容量') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="120"
        :required="false"
        :row-width="rowWidth"
        :width="180">
        <span>{{ $t('指定Redis版本') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-minimum="isMinimum"
        :min-width="110"
        :required="false"
        :row-width="rowWidth"
        :width="160">
        <span>{{ $t('切换模式') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :is-fixed="isFixed"
        :is-minimum="isMinimum"
        :min-width="90"
        :required="false"
        :row-width="rowWidth"
        :width="100">
        {{ $t('操作') }}
      </RenderTableHeadColumn>
      <template #data>
        <slot />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/redis/common/render-table/Index.vue';

  interface Emits{
    (e: 'showBatchSelector'): void,
    (e: 'scroll-display', status: boolean): void
  }

  const emits = defineEmits<Emits>();

  const isFixed = ref(false);

  const rowWidth = ref(0);

  const isMinimum = ref(false);

  const handleRowWidthChange = (width: number) =>  rowWidth.value = width;

  const handleScrollDisplay = (isShow: boolean) => {
    isFixed.value = isShow;
    isMinimum.value = isShow;
    emits('scroll-display', isShow);
  };

  const handleShowMasterBatchSelector = () => {
    emits('showBatchSelector');
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
