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
      {{ t('待回档集群') }}
      <template #append>
        <BatchOperateIcon
          class="ml-4"
          @click="handleShowBatchSelector" />
      </template>
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="200"
      :width="250">
      {{ t('目标集群') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="120"
      :width="150">
      <template #append>
        <BatchEditColumn
          v-model="isShowBatchEdit.backupSource"
          :data-list="selectList.backupSource"
          :title="t('备份源')"
          @change="(value) => handleBatchEdit('backupSource', value)">
          <BatchOperateIcon
            class="ml-4"
            type="edit"
            @click="handleShowBatchEdit('backupSource')" />
        </BatchEditColumn>
      </template>
      {{ t('备份源') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="380"
      :width="400">
      <template #append>
        <BatchEditColumn
          v-model="isShowBatchEdit.mode"
          :title="t('回档类型')"
          @change="handleBatchModeEdit">
          <template #content>
            <div
              class="title-spot edit-title"
              style="font-weight: normal">
              {{ t('回档类型') }} <span class="required" />
            </div>
            <BkSelect
              v-model="checkedModeType"
              :clearable="false"
              filterable
              :list="selectList.mode"
              @change="handleModeType" />
            <div v-if="checkedModeType === BackupTypes.TIME">
              <div
                class="title-spot edit-title mt-24"
                style="font-weight: normal">
                {{ t('时间') }} <span class="required" />
              </div>
              <BkDatePicker
                :clearable="false"
                :placeholder="t('如：2019-01-30 12:12:21')"
                style="width: 361px"
                type="datetime"
                :value="datePickerValue"
                @change="handleDatePickerChange" />
            </div>
            <div v-else>
              <div
                class="title-spot edit-title mt-24"
                style="font-weight: normal">
                {{ t('备份文件 (批量编辑仅支持 “指定时间自动匹配” )') }} <span class="required" />
              </div>
              <BkDatePicker
                :clearable="false"
                :placeholder="t('如：2019-01-30 12:12:21')"
                style="width: 361px"
                type="datetime"
                :value="datePickerValue"
                @change="handleDatePickerChange" />
              <div
                class="mt-4"
                :style="{ color: '#979ba5', lineHeight: '20px' }">
                {{ t('自动匹配指定日期前的最新全库备份') }}
              </div>
            </div>
          </template>
        </BatchEditColumn>
        <BatchOperateIcon
          class="ml-4"
          type="edit"
          @click="handleShowBatchEdit('mode')" />
      </template>
      {{ t('回档类型') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="150"
      :width="200">
      <template #append>
        <BatchEditColumn
          v-model="isShowBatchEdit.databases"
          :placeholder="t('请输入,如需输入多个用回车换行')"
          :title="t('回档DB')"
          type="textarea"
          @change="(value) => handleBatchEdit('databases', value, true)">
          <BatchOperateIcon
            class="ml-4"
            type="edit"
            @click="handleShowBatchEdit('databases')" />
        </BatchEditColumn>
      </template>
      {{ t('回档DB') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="150"
      :required="false"
      :width="200">
      <template #append>
        <BatchEditColumn
          v-model="isShowBatchEdit.databasesIgnore"
          :placeholder="t('请输入,如需输入多个用回车换行')"
          :title="t('忽略DB')"
          type="textarea"
          @change="(value) => handleBatchEdit('databasesIgnore', value, true)">
          <BatchOperateIcon
            class="ml-4"
            type="edit"
            @click="handleShowBatchEdit('databasesIgnore')" />
        </BatchEditColumn>
      </template>
      {{ t('忽略DB') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="150"
      :width="200">
      <template #append>
        <BatchEditColumn
          v-model="isShowBatchEdit.tables"
          :placeholder="t('请输入,如需输入多个用回车换行')"
          :title="t('回档表名')"
          type="textarea"
          @change="(value) => handleBatchEdit('tables', value, true)">
          <BatchOperateIcon
            class="ml-4"
            type="edit"
            @click="handleShowBatchEdit('tables')" />
        </BatchEditColumn>
      </template>
      {{ t('回档表名') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :min-width="150"
      :required="false"
      :width="200">
      <template #append>
        <BatchEditColumn
          v-model="isShowBatchEdit.tablesIgnore"
          :placeholder="t('请输入,如需输入多个用回车换行')"
          :title="t('忽略表名')"
          type="textarea"
          @change="(value) => handleBatchEdit('tablesIgnore', value, true)">
          <BatchOperateIcon
            class="ml-4"
            type="edit"
            @click="handleShowBatchEdit('tablesIgnore')" />
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

  import { BackupTypes, selectList } from '../../common/const';
  import type { IDataRow } from '../Index.vue';

  interface Emits {
    (e: 'showSelector'): void;
    (e: 'batchEdit', obj: Record<string, any>): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const checkedModeType = ref(BackupTypes.BACKUPID);
  const datePickerValue = ref('');
  const isShowBatchEdit = reactive({
    backupSource: false,
    mode: false,
    databases: false,
    databasesIgnore: false,
    tables: false,
    tablesIgnore: false,
  });

  const handleModeType = (value: BackupTypes) => {
    checkedModeType.value = value;
  };
  const handleDatePickerChange = (date: string) => {
    datePickerValue.value = date;
  };
  const handleBatchModeEdit = () => {
    if (checkedModeType.value === BackupTypes.TIME) {
      handleBatchEdit('rollbackTime', datePickerValue.value);
      handleBatchEdit('backupid', '');
    } else {
      handleBatchEdit('backupid', datePickerValue.value);
      handleBatchEdit('rollbackTime', '');
    }
  };

  const handleShowBatchEdit = (col: keyof typeof isShowBatchEdit) => {
    isShowBatchEdit[col] = !isShowBatchEdit[col];
  };

  const handleShowBatchSelector = () => {
    emits('showSelector');
  };

  const handleBatchEdit = (key: keyof IDataRow, value: string, isArray = false) => {
    emits('batchEdit', {
      [key]: isArray && value ? value.split('\n') : value,
    });
  };
</script>
