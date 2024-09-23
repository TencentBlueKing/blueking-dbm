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
  <div class="db-table-backup-render-data">
    <RenderTable>
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :width="180">
          {{ t('目标集群') }}
          <template #append>
            <span
              class="batch-edit-btn"
              @click="handleShowBatchSelector">
              <DbIcon type="batch-host-select" />
            </span>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="110">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.scope"
              :data-list="selectList"
              :title="t('校验范围')"
              @change="(value) => handleBatchEditChange(value, 'scope')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('scope')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('校验范围') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="90"
          :required="false"
          :width="160">
          {{ t('校验从库') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="90"
          :required="false"
          :width="140">
          {{ t('校验主库') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="170">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.dbPatterns"
              :title="t('校验DB名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'dbPatterns')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('dbPatterns')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('校验DB名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="170">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.ignoreDbs"
              :title="t('忽略DB名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'ignoreDbs')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('ignoreDbs')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('忽略DB名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="170">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.tablePatterns"
              :title="t('校验表名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'tablePatterns')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('tablePatterns')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('校验表名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="170">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.ignoreTables"
              :title="t('忽略表名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'ignoreTables')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('ignoreTables')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('忽略表名') }}
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

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import type { IDataRowBatchKey } from './Row.vue';

  interface Emits {
    (e: 'batchSelectCluster'): void;
    (e: 'batchEdit', value: string | string[], filed: IDataRowBatchKey): void;
  }
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const batchEditShow = reactive({
    scope: false,
    dbPatterns: false,
    ignoreDbs: false,
    tablePatterns: false,
    ignoreTables: false,
  });

  const selectList = [
    {
      value: 'all',
      label: t('整个集群'),
    },
    {
      value: 'partial',
      label: t('部分实例'),
    },
  ];

  const handleBatchEditShow = (key: IDataRowBatchKey) => {
    batchEditShow[key] = !batchEditShow[key];
  };

  const handleBatchEditChange = (value: string | string[], filed: IDataRowBatchKey) => {
    emits('batchEdit', value, filed);
  };

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };
</script>
<style lang="less">
  .db-table-backup-render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
