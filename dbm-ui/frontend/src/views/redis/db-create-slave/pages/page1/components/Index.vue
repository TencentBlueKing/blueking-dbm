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
          :is-minimize="slotProps.isOverflow"
          :min-width="150"
          :row-width="slotProps.rowWidth"
          :width="280">
          <span>{{ $t('目标主库主机') }}</span>
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
          :is-minimize="slotProps.isOverflow"
          :min-width="180"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="280">
          <span>{{ $t('所属集群') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-minimize="slotProps.isOverflow"
          :min-width="150"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="300">
          <BkPopover
            :content="$t('默认使用部署方案中选定的规格，将从资源池自动匹配机器')"
            placement="top"
            theme="dark">
            <span class="spec-title">{{ $t('规格需求') }}</span>
          </BkPopover>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-minimize="slotProps.isOverflow"
          :min-width="150"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="190">
          <span>{{ $t('当前从库主机') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-fixed="slotProps.isOverflow"
          :is-minimize="slotProps.isOverflow"
          :min-width="90"
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
  import RenderTable from '@components/render-table/Index.vue';

  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';

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

.spec-title {
  border-bottom: 1px dashed #979BA5;
}
</style>
