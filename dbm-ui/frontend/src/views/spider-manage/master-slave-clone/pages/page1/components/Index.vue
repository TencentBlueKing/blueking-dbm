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
      <RenderTableHeadColumn :min-width="150">
        {{ t('目标主库主机') }}
        <template #append>
          <span
            class="batch-edit-btn"
            @click="handleShowBatchSelector">
            <DbIcon type="batch-host-select" />
          </span>
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        {{ t('主库主机关联实例') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        {{ t('目标从库主机') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        {{ t('从库主机关联实例') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        {{ t('所属集群') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        {{ t('新实例') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :required="false"
        :width="90">
        {{ t('操作') }}
      </RenderTableHeadColumn>
      <template #data>
        <slot />
      </template>
    </RenderTable>
  </div>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  interface Emits {
    (e: 'showMasterBatchSelector'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleShowBatchSelector = () => {
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
    border-bottom: 1px dashed #979ba5;
  }
</style>
