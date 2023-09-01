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
          :min-width="120"
          :row-width="slotProps.rowWidth"
          :width="330">
          <span>{{ t('故障主库主机') }}</span>
          <template #append>
            <span
              class="batch-edit-btn"
              @click="handleShowMasterBatchSelector">
              <DbIcon type="batch-host-select" />
            </span>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-minimize="slotProps.isOverflow"
          :min-width="120"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="440">
          <span>{{ t('从库主机') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-minimize="slotProps.isOverflow"
          :min-width="120"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="440">
          <span>{{ t('所需集群') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-fixed="slotProps.isOverflow"
          :is-minimize="slotProps.isOverflow"
          :min-width="90"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="100">
          {{ t('操作') }}
        </RenderTableHeadColumn>
      </template>
      <template #data="slotProps">
        <slot :is-overflow="slotProps.isOverflow" />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  interface Emits{
    (e: 'showMasterBatchSelector'): void,
    (e: 'showSlaveBatchSelector'): void,
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleShowMasterBatchSelector = () => {
    emits('showMasterBatchSelector');
  };
</script>
<style lang="less" scoped>
  .render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
