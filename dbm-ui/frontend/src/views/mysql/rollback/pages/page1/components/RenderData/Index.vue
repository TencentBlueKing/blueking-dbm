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
      <RenderTableHeadColumn
        :min-width="130"
        :width="150">
        {{ t('待回档集群') }}
        <template #append>
          <span
            class="batch-edit-btn"
            @click="handleShowBatchSelector">
            <DbIcon type="batch-host-select" />
          </span>
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="180"
        :width="180">
        {{ t('回档到新主机') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="100"
        :width="120">
        {{ t('备份源') }}
        <template #append>
          <BatchEditColumn
            v-model="batchEditShow.backupSource"
            :data-list="backupSourceList"
            :title="t('备份源')"
            @change="(value) => handleBatchEditChange(value, 'backupSource')">
            <span
              v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
              class="batch-edit-btn"
              @click="handleBatchEditShow('backupSource')">
              <DbIcon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="240"
        :width="260">
        {{ t('回档类型') }}
        <template #append>
          <BatchEditColumn
            v-model="batchEditShow.backupid"
            :data-list="backupIdList"
            :title="t('回档类型')"
            @change="(value) => handleBatchEditChange(value, 'backupid')">
            <span
              v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
              class="batch-edit-btn"
              @click="handleBatchEditShow('backupid')">
              <DbIcon type="bulk-edit" />
            </span>
          </BatchEditColumn>
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="100"
        :width="120">
        {{ t('回档DB名') }}
        <template #append>
          <BatchEditColumn
            v-model="batchEditShow.databases"
            :title="t('回档DB名')"
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
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="100"
        :width="120">
        {{ t('回档表名') }}
        <template #append>
          <BatchEditColumn
            v-model="batchEditShow.tables"
            :title="t('回档表名')"
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
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="100"
        :required="false"
        :width="120">
        {{ t('忽略DB名') }}
        <template #append>
          <BatchEditColumn
            v-model="batchEditShow.databasesIgnore"
            :title="t('忽略DB名')"
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
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="100"
        :required="false"
        :width="120">
        {{ t('忽略表名') }}
        <template #append>
          <BatchEditColumn
            v-model="batchEditShow.tablesIgnore"
            :title="t('忽略表名')"
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

  const batchEditShow = reactive({
    backupSource: false,
    backupid: false,
    databases: false,
    tables: false,
    databasesIgnore: false,
    tablesIgnore: false,
  });

  const backupSourceList = [
    {
      value: 'remote',
      label: t('远程备份'),
    },
    {
      value: 'local',
      label: t('本地备份'),
    },
  ];

  const backupIdList = [
    {
      value: 'record',
      label: t('备份记录'),
    },
    {
      value: 'time',
      label: t('回档到指定时间'),
    },
  ];

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
