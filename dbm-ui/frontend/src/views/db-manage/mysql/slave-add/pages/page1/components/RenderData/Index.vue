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
  <RenderTable>
    <RenderTableHeadColumn
      fixed="left"
      :min-width="300"
      :width="350">
      {{ t('目标集群') }}
      <template #append>
        <BatchOperateIcon
          class="ml-4"
          @click="handleShowBatchSelector" />
      </template>
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="200"
      :width="280">
      {{ t('新主从主机') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      fixed="right"
      :required="false"
      :width="90">
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

  import BatchOperateIcon from '@views/db-manage/common/batch-operate-icon/Index.vue';

  interface Emits {
    (e: 'batchSelectCluster'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };
</script>
