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
  <RenderTable class="cluster-standardize-table">
    <RenderTableHeadColumn
      :required="false"
      :show-overflow-tooltip="false">
      {{ t('目标集群') }}
      <template #append>
        <BkButton
          v-bk-tooltips="t('批量选择')"
          class="ml-4"
          text
          theme="primary"
          @click="handleShowBatchSelector">
          <DbIcon type="batch-host-select" />
        </BkButton>
      </template>
    </RenderTableHeadColumn>
    <RenderTableHeadColumn :required="false">
      {{ t('集群类型') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn :required="false">
      {{ t('归属业务') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn :required="false">
      {{ t('状态') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      fixed="right"
      :required="false"
      :width="150">
      {{ t('操作') }}
    </RenderTableHeadColumn>
    <template #data>
      <slot />
    </template>
  </RenderTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  interface Emits {
    (e: 'batchSelectCluster'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };
</script>

<style lang="less" scoped>
  .cluster-standardize-table {
    margin-bottom: 0;
    overflow: initial;
  }
</style>
