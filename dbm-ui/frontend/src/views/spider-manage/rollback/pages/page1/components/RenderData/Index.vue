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
          :min-width="120"
          :width="190">
          {{ t('待构造集群') }}
          <template #append>
            <span
              class="batch-edit-btn"
              @click="handleShowBatchSelector">
              <DbIcon type="batch-host-select" />
            </span>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="320"
          :width="450">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.rollbackupType"
              :data-list="selectList"
              :title="t('回档类型')"
              @change="(value) => handleBatchEditChange(value, 'rollbackupType')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('rollbackupType')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('回档类型') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="120">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.databases"
              :title="t('备份DB名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'databases')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('databases')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('构造 DB 名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="120">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.databasesIgnore"
              :title="t('备份DB名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'databasesIgnore')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('databasesIgnore')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('忽略DB名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="120">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.tables"
              :title="t('备份DB名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'tables')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('tables')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('构造表名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="120">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.tablesIgnore"
              :title="t('备份DB名')"
              type="taginput"
              @change="(value) => handleBatchEditChange(value, 'tablesIgnore')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('tablesIgnore')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('忽略表名') }}
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

  import BatchEditColumn from '@components/batch-edit-column/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import type { IDataRowBatchKey } from './Row.vue';

  interface Emits {
    (e: 'batchSelectCluster'): void;
    (e: 'batchEdit', value: string | string[], filed: IDataRowBatchKey): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const selectList = [
    {
      value: 'REMOTE_AND_BACKUPID',
      label: t('备份记录'),
    },
    {
      value: 'REMOTE_AND_TIME',
      label: t('回档到指定时间'),
    },
  ];

  const batchEditShow = reactive({
    rollbackupType: false,
    databases: false,
    databasesIgnore: false,
    tables: false,
    tablesIgnore: false,
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
<style lang="less">
  .render-data {
    display: block;

    .batch-edit-btn {
      display: inline-block;
      margin-left: 4px;
      line-height: 40px;
      color: #3a84ff;
      vertical-align: top;
      cursor: pointer;
    }
  }
</style>
