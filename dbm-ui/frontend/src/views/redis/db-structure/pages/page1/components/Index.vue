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
      <template #default>
        <RenderTableHeadColumn
          :min-width="140"
          :width="240">
          <span>{{ $t('待构造的集群') }}</span>
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
          :max-width="200"
          :min-width="120"
          :width="200">
          <span>{{ $t('待构造的实例') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="130"
          :required="false"
          :width="240">
          <BkPopover
            :content="$t('默认使用部署时选定的规格，将从资源池自动匹配机器')"
            theme="dark">
            <span class="spec-title">{{ $t('规格需求') }}</span>
          </BkPopover>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="120">
          <span>{{ $t('构造主机数量') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="160"
          :width="220">
          <span>{{ $t('构造到指定时间') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          fixed="right"
          :required="false"
          :width="100">
          {{ $t('操作') }}
        </RenderTableHeadColumn>
      </template>

      <template #data>
        <slot />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  interface Emits{
    (e: 'showBatchSelector'): void,
  }

  const emits = defineEmits<Emits>();

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

.spec-title {
  border-bottom: 1px dashed #979BA5;
}
</style>
