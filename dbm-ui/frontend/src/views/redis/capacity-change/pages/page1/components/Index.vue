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
          :min-width="130"
          :width="300">
          <span>{{ t('目标集群') }}</span>
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
          :min-width="120"
          :required="false"
          :width="200">
          <span>{{ t('架构版本') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :width="180">
          <span>{{ t('Redis版本') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="240"
          :required="false">
          <span>{{ t('当前容量') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn :min-width="350">
          <span>{{ t('目标容量') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :required="false"
          :width="130">
          <span>{{ t('切换模式') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          fixed="right"
          :required="false"
          :width="100">
          {{ t('操作') }}
        </RenderTableHeadColumn>
      </template>

      <template #data>
        <slot />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  interface Emits {
    (e: 'showBatchSelector'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

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
