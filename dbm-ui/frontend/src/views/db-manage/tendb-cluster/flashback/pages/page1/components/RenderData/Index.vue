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
          :width="200">
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
          :min-width="170"
          :width="180">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.startTime"
              :disable-fn="disabledStartTime"
              :title="t('回档时间')"
              type="datetime"
              @change="(value) => handleBatchEditChange(value, 'startTime')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('startTime')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('回档时间') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="170"
          :width="180">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.endTime"
              :disable-fn="disabledEndTime"
              :title="t('截止时间')"
              type="datetime"
              @change="(value) => handleBatchEditChange(value, 'endTime')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('endTime')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
          {{ t('截止时间') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="190">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.databases"
              :title="t('目标库')"
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
          {{ t('目标库') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="180">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.databasesIgnore"
              :title="t('忽略库')"
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
          {{ t('忽略库') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="350">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.tables"
              :title="t('目标表')"
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
          {{ t('目标表') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="180">
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.tablesIgnore"
              :title="t('忽略表')"
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
          {{ t('忽略表') }}
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
  import dayjs from 'dayjs';
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

  const startTime = ref('');
  const batchEditShow = reactive({
    startTime: false,
    endTime: false,
    databases: false,
    tables: false,
    databasesIgnore: false,
    tablesIgnore: false,
  });

  const disabledStartTime = (date?: Date | number) => !!date && date.valueOf() > Date.now();

  const disabledEndTime = (date?: Date | number) =>
    !!date && (date.valueOf() > Date.now() || date.valueOf() < dayjs(startTime.value).valueOf());

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };

  const handleBatchEditShow = (key: IDataRowBatchKey) => {
    batchEditShow[key] = !batchEditShow[key];
  };

  const handleBatchEditChange = (value: string | string[], filed: IDataRowBatchKey) => {
    if (filed === 'startTime') {
      startTime.value = value as string;
    }
    emits('batchEdit', value, filed);
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
