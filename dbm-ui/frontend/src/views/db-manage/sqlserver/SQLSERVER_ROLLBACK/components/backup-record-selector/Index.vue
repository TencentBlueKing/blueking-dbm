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
  <BkDialog
    class="sqlserver-backup-record-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :title="t('选择备份记录')"
    :width="dialogWidth"
    @closed="handleClose">
    <div class="align-center mb-12">
      <div
        class="align-center mr-8"
        style="flex: 1">
        <div class="backup-time-picker">{{ t('备份时间') }}</div>
        <BkDatePicker
          v-model="daterange"
          append-to-body
          clearable
          :disabled-date="disableDate"
          :placeholder="t('请选择')"
          :shortcuts="shortcuts"
          style="width: 100%"
          type="datetimerange"
          @change="handleDateChange"
          @clear="handleDateClear" />
      </div>
      <DbQuickSearch
        v-model="searchSelectValue"
        :data="searchSelectData"
        parse-url
        :placeholder="t('搜索备份记录')"
        style="flex: 1" />
    </div>
    <BkLoading :loading="loading">
      <PrimaryTable
        ref="tableRef"
        :data="renderData"
        :height="500"
        :max-height="tableMaxHeight"
        row-key="backup_id">
        <TableColumn
          col-key="end_time"
          :title="t('备份时间')"
          :width="230">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            <BkRadio
              v-model="checkedBackupId"
              :label="row.backup_id"
              @change="() => handleChecked(row)">
              {{ utcDisplayTime(row.end_time) }}
            </BkRadio>
          </template>
        </TableColumn>
        <TableColumn
          col-key="role"
          :title="t('角色')"
          :width="80">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            {{ row.role }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="backup_id"
          ellipsis
          :title="t('备份 ID')"
          :width="260">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            {{ row.backup_id }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="backup_db_list"
          :title="t('备份包含库')"
          :width="260">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            <BackupDbTags :list="row.backup_db_list" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="excluded_db_list"
          :title="t('备份缺失库')"
          :width="260">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            <BackupDbTags
              :list="row.excluded_db_list"
              theme="warning" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="backup_db_size_kb"
          :title="t('数据库大小')"
          :width="120">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            {{ bytePretty((row.backup_db_size_kb ?? 0) * 1024) }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="backup_file_size_kb"
          :title="t('备份文件大小')"
          :width="120">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            {{ bytePretty((row.backup_file_size_kb ?? 0) * 1024) }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="bill_id"
          :min-width="120"
          :title="t('关联单据')">
          <template #default="{ row }: { row: SqlserverBackupLogModel }">
            <RouterLink
              v-if="row.bill_id"
              target="_blank"
              :to="{
                name: 'ticketDetail',
                params: {
                  ticketId: row.bill_id,
                },
              }">
              {{ row.bill_id }}
            </RouterLink>
            <span v-else>--</span>
          </template>
        </TableColumn>
      </PrimaryTable>
      <div
        v-if="pagination.count > 0"
        class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          :model-value="pagination.current"
          @change="handleChangePage"
          @limit-change="handeChangeLimit" />
      </div>
    </BkLoading>
    <template #footer>
      <div class="sqlserver-backup-record-selector-footer">
        <div class="align-center">
          <div class="footer-text">{{ t('已选择：') }}</div>
          <div
            v-if="localValue?.backup_id"
            class="footer-text"
            style="font-weight: bold">
            {{ `${localValue?.role} ${utcDisplayTime(localValue?.end_time)}` }}
          </div>
          <div v-else>--</div>
          <BkButton
            class="ml-8"
            text
            theme="primary"
            @click="handeClear">
            {{ t('清空') }}
          </BkButton>
        </div>
        <div class="align-center footer-btn">
          <BkButton
            class="cluster-selector-button mr-8"
            theme="primary"
            @click="handleConfirm">
            {{ t('确定') }}
          </BkButton>
          <BkButton
            class="cluster-selector-button"
            @click="handleClose">
            {{ t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import SqlserverBackupLogModel from '@services/model/sqlserver/backup-log';
  import { queryBackupLogs } from '@services/source/sqlserver';

  import { useDefaultPagination, useSelectorDialogWidth, useTableMaxHeight } from '@hooks';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  import { bytePretty, utcDisplayTime } from '@utils';

  import BackupDbTags from '../BackupDbTags.vue';

  interface Props {
    backupTime?: string;
    cluster: {
      id: number;
    };
  }

  type Emits = (e: 'change', data?: SqlserverBackupLogModel) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const modelValue = defineModel<SqlserverBackupLogModel>();

  const { dialogWidth } = useSelectorDialogWidth();
  const tableMaxHeight = useTableMaxHeight(240);
  const { t } = useI18n();

  const localValue = ref<SqlserverBackupLogModel>();
  const tableRef = ref();
  const daterange = ref<[string, string] | [Date, Date]>(['', '']);
  const comfirmDaterange = ref<[string, string] | [Date, Date]>(daterange.value);
  const searchSelectValue = ref<Record<string, string>>({});
  const searchSelectData = [
    {
      id: 'backup_id',
      name: t('备份 ID'),
    },
    {
      id: 'role',
      name: t('角色'),
    },
    {
      id: 'backup_db_list',
      name: t('备份包含库'),
    },
    {
      id: 'bill_id',
      name: t('关联单据'),
    },
  ] as QuickSearchProps['data'];
  const originalData = shallowRef<SqlserverBackupLogModel[]>([]);
  const tableData = shallowRef<SqlserverBackupLogModel[]>([]);
  const pagination = ref(useDefaultPagination());
  const loading = ref(false);
  const checkedBackupId = ref<string>();
  const filteredData = shallowRef<SqlserverBackupLogModel[]>([]);

  const renderData = computed(() => {
    const [start, end] = comfirmDaterange.value;
    const dateParams =
      start && end
        ? {
            end_time: new Date(end).getTime(),
            start_time: new Date(start).getTime(),
          }
        : undefined;

    const searchParams = searchSelectValue.value;

    filteredData.value = [];
    tableData.value.forEach((row) => {
      const timerange = {
        end_time: new Date(row.end_time).getTime(),
        start_time: new Date(row.end_time).getTime(),
      };
      const isTimeMatch = !dateParams
        ? true
        : timerange.start_time >= dateParams.start_time && timerange.end_time <= dateParams.end_time;

      // Multi-field search match
      let isSearchMatch = true;
      if (searchParams.backup_id) {
        isSearchMatch = row.backup_id.toLowerCase().includes(searchParams.backup_id.toLowerCase());
      }
      if (isSearchMatch && searchParams.role) {
        isSearchMatch = row.role.toLowerCase().includes(searchParams.role.toLowerCase());
      }
      if (isSearchMatch && searchParams.backup_db_list) {
        isSearchMatch = row.backup_db_list.some((dbName) =>
          dbName.toLowerCase().includes(searchParams.backup_db_list.toLowerCase()),
        );
      }
      if (isSearchMatch && searchParams.bill_id) {
        isSearchMatch = row.bill_id.toLowerCase().includes(searchParams.bill_id.toLowerCase());
      }

      if (isTimeMatch && isSearchMatch) {
        filteredData.value.push(row);
      }
    });

    const { current, limit } = pagination.value;
    const startIndex = (current - 1) * limit;
    const endIndex = startIndex + limit;
    return filteredData.value.slice(startIndex, endIndex);
  });

  watch(filteredData, () => {
    pagination.value.count = filteredData.value.length || tableData.value.length;
  });

  const handleChecked = (row: SqlserverBackupLogModel) => {
    checkedBackupId.value = row.backup_id;
    localValue.value = originalData.value.find((item) => item.backup_id === row.backup_id);
  };

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    tableRef.value!.scrollToElement({ index: 0, top: 44 });
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    handleChangePage(1);
  };

  const disableDate = (date?: Date | number) =>
    dayjs(date).isAfter(props.backupTime ? dayjs(props.backupTime) : dayjs(), 'day');

  const shortcuts = [
    {
      text: t('今天'),
      value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
    },
    {
      text: t('近 7 天'),
      value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
    },
    {
      text: t('近 15 天'),
      value: () => [dayjs().subtract(14, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
    },
    {
      text: t('近 30 天'),
      value: () => [dayjs().subtract(29, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
    },
  ];

  const handleDateChange = () => {
    comfirmDaterange.value = daterange.value;
  };

  const handleDateClear = () => {
    comfirmDaterange.value = ['', ''];
  };

  const fetchData = async () => {
    try {
      loading.value = true;
      const results = await queryBackupLogs({
        cluster_id: props.cluster.id,
        end_time: props.backupTime,
      });

      originalData.value = results;
      tableData.value = results;

      pagination.value.count = results.length;
      checkedBackupId.value = modelValue.value?.backup_id;
      localValue.value = modelValue.value;
    } catch {
      tableData.value = [];
      pagination.value.count = 0;
      checkedBackupId.value = undefined;
      localValue.value = undefined;
    } finally {
      loading.value = false;
    }
  };

  const handeClear = () => {
    checkedBackupId.value = undefined;
    modelValue.value = undefined;
    localValue.value = undefined;
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = () => {
    modelValue.value = localValue.value;
    emits('change', localValue.value);
    isShow.value = false;
  };

  watch(isShow, () => {
    if (isShow.value) {
      fetchData();
    }
  });
</script>
<style lang="less">
  .sqlserver-backup-record-selector {
    .align-center {
      display: flex;
      align-items: center;
    }

    .backup-time-picker {
      display: flex;
      width: 71px;
      height: 32px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 12px;
      line-height: 20px;
      letter-spacing: 0;
      color: #4d4f56;
      background: #fafbfd;
      border: 1px solid #c4c6cc;
      border-right: none;
      border-radius: 2px 0 0 2px;
      align-items: center;
      justify-content: center;
    }

    .table-footer {
      display: flex;
      margin-top: 12px;
      justify-content: flex-end;
    }

    .sqlserver-backup-record-selector-footer {
      position: relative;
      display: flex;
      align-items: center;
      height: 40px;

      .footer-text {
        font-family: MicrosoftYaHei, sans-serif;
        font-size: 12px;
        line-height: 0;
        letter-spacing: 0;
        color: #4d4f56;
        text-align: left;
      }

      .footer-btn {
        position: absolute;
        right: 0;
      }
    }
  }
</style>
