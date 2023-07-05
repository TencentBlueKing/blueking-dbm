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
      <RenderTableHeadColumn>
        <span>{{ $t('待替换的主机') }}</span>
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
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('角色类型') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('所属集群') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <BkPopover
          :content="$t('默认使用部署方案中选定的规格，将从资源池自动匹配机器')"
          theme="dark">
          <span class="spec-title">{{ $t('规格需求') }}</span>
        </BkPopover>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :required="false"
        :width="90">
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
    (e: 'showMasterBatchSelector'): void,
    (e: 'showSlaveBatchSelector'): void,
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

.spec-title {
  border-bottom: 1px dashed #979BA5;
}
</style>
