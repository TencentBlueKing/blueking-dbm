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
          :min-width="100"
          :width="270">
          <span>{{ $t('源集群') }}</span>
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
          :min-width="110"
          :required="false"
          :width="140">
          <span>{{ $t('原集群类型') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="110"
          :required="false"
          :width="140">
          <span>{{ $t('目标集群类型') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :width="350">
          <span>{{ $t('当前集群容量/QPS') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :width="350">
          <BkPopover
            :content="$t('将会部署新的集群以进行集群变更')"
            placement="top"
            theme="dark">
            <span style="border-bottom: 1px dashed #979BA5;">{{ $t('部署方案') }}</span>
          </BkPopover>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="140">
          <span>{{ $t('版本') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :width="240">
          <BkPopover
            :content="$t('后端存储实例与 Proxy 的关系切换')"
            placement="top"
            theme="dark">
            <span style="border-bottom: 1px dashed #979BA5;">{{ $t('切换模式') }}</span>
          </BkPopover>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          fixed="right"
          :required="false"
          :width="120">
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
