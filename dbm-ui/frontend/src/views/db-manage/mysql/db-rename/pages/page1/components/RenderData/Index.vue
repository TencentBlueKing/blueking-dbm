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
    <template #default>
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
        :min-width="100"
        :width="400">
        {{ t('源 DB 名') }}
        <BatchEditColumn
          v-model="batchEditShow.fromDatabase"
          :title="t('源 DB 名')"
          type="input"
          @change="(value) => handleBatchEditChange(value, 'fromDatabase')">
          <span
            v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
            class="batch-edit-btn"
            @click="handleBatchEditShow('fromDatabase')">
            <DbIcon type="bulk-edit" />
          </span>
        </BatchEditColumn>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="100"
        :width="400">
        {{ t('新 DB 名') }}
        <BatchEditColumn
          v-model="batchEditShow.toDatabase"
          :title="t('新 DB 名')"
          type="input"
          @change="(value) => handleBatchEditChange(value, 'toDatabase')">
          <span
            v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
            class="batch-edit-btn"
            @click="handleBatchEditShow('toDatabase')">
            <DbIcon type="bulk-edit" />
          </span>
        </BatchEditColumn>
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
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';
  import BatchOperateIcon from '@views/db-manage/common/batch-operate-icon/Index.vue';

  import type { IDataRowBatchKey } from './Row.vue';

  interface Emits {
    (e: 'batchSelectCluster'): void;
    (e: 'batchEdit', value: string | string[], filed: IDataRowBatchKey): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const batchEditShow = reactive({
    fromDatabase: false,
    toDatabase: false,
  });

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };

  const handleBatchEditShow = (key: IDataRowBatchKey) => {
    batchEditShow[key] = !batchEditShow[key];
  };

  const handleBatchEditChange = (value: string | string[], filed: IDataRowBatchKey) => {
    emits('batchEdit', value, filed);
  };
</script>
