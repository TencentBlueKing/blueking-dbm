<template>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="backupTime"
    :label="t('指定时间')"
    :min-width="240"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('指定时间')"
        title-prefix-type="select"
        @change="handleBatchEdit">
        <template #content>
          <DbForm
            form-type="vertical"
            :model="formData">
            <BkFormItem
              field="backup_time"
              :label="t('指定时间（提交后自动选择与指定时间最近的全备记录文件）')"
              required>
              <BkDatePicker
                v-model="formData.backup_time"
                :clearable="false"
                :disabled-date="disableDate"
                :placeholder="t('请选择指定时间')"
                style="width: 360px"
                type="datetime" />
            </BkFormItem>
          </DbForm>
        </template>
      </BatchEditColumn>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select"
        @click="handleShowBatchEdit">
        <DbIcon type="bulk-edit" />
      </span>
    </template>
    <EditableDatePicker
      v-model="backupTime"
      :disabled-date="disableDate"
      :placeholder="t('请选择指定时间')"
      type="datetime"
      @change="handleDateChange">
    </EditableDatePicker>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="backupRecord"
    :label="t('备份记录')"
    :min-width="370"
    required>
    <EditableBlock
      v-if="backupRecord?.backup_id"
      style="width: 100%"
      @click="handleShowSelector">
      <div class="content-block">
        <div class="content-label">{{ t('备份记录 ：') }}</div>
        <div class="content-value">{{ utcDisplayTime(backupRecord.end_time) }}</div>
        <div class="content-label">{{ t('备份角色 ：') }}</div>
        <div class="content-value">
          {{ backupRecord.role }}
        </div>
        <div class="content-label">{{ t('备份 ID ：') }}</div>
        <div class="content-value">
          {{ backupRecord.backup_id || '--' }}
        </div>
        <div class="content-label">{{ t('备份包含库 ：') }}</div>
        <div class="content-value">
          <BackupDbTags :list="backupRecord.backup_db_list" />
        </div>
        <div class="content-label">{{ t('备份缺失库 ：') }}</div>
        <div class="content-value">
          <BackupDbTags
            :list="backupRecord.excluded_db_list"
            theme="warning" />
        </div>
        <div class="content-label">{{ t('数据库大小 ：') }}</div>
        <div class="content-value">{{ bytePretty((backupRecord.backup_db_size_kb ?? 0) * 1024) }}</div>
        <div class="content-label">{{ t('备份文件大小 ：') }}</div>
        <div class="content-value">{{ bytePretty(backupRecord.backup_file_size_kb * 1024) }}</div>
        <div
          v-if="backupRecord.bill_id"
          class="content-label">
          {{ t('关联单据 ：') }}
        </div>
        <div
          v-if="backupRecord.bill_id"
          class="content-value">
          <RouterLink
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: backupRecord.bill_id,
              },
            }">
            {{ backupRecord.bill_id }}
          </RouterLink>
        </div>
      </div>
      <DbIcon
        class="content-icon"
        type="down-big" />
    </EditableBlock>
    <EditableSelect
      v-else-if="backupTime"
      :placeholder="t('未匹配到备份记录，请选择')"
      :popover-options="{
        boundary: 'parent',
        trigger: 'manual',
        isShow: false,
      }"
      @click="handleShowSelector" />
    <EditableBlock
      v-else
      :placeholder="t('自动生成')" />
  </EditableColumn>
  <BackupRecordSelector
    v-model="backupRecord"
    v-model:is-show="isShowSelector"
    :backup-time="backupTime"
    v-bind="props" />
</template>
<script lang="ts" setup>
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlserverBackupLogModel from '@services/model/sqlserver/backup-log';
  import { queryLatestBackupLog } from '@services/source/sqlserver';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import { bytePretty, utcDisplayTime } from '@utils';

  import BackupRecordSelector from '../backup-record-selector/Index.vue';
  import BackupDbTags from '../BackupDbTags.vue';

  interface Props {
    cluster: {
      id: number;
      master_domain: string;
    };
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    flush: () => void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const backupTime = defineModel<string>('backupTime', {
    required: true,
  });

  const backupRecord = defineModel<SqlserverBackupLogModel | undefined>('backupRecord', {
    required: true,
  });

  const tableData = defineModel<
    {
      backupRecord: SqlserverBackupLogModel | undefined;
      backupTime: string;
      cluster: Props['cluster'];
    }[]
  >('tableData', {
    required: true,
  });

  const { t } = useI18n();

  const isShowSelector = ref(false);
  const isShowBatchEdit = ref(false);
  const formData = ref({
    backup_time: '',
  });

  const { run: fetchData } = useRequest(queryLatestBackupLog, {
    manual: true,
    onSuccess(data) {
      backupRecord.value = data;
    },
  });

  const disabledMethod = () => (props.cluster.id ? false : t('请先选择集群'));
  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleDateChange = (date: string) => {
    backupTime.value = date;
    fetchData({
      cluster_id: props.cluster.id,
      rollback_time: date,
    });
  };

  const handleBatchEdit = async () => {
    Promise.all(
      tableData.value.map((rowData) =>
        queryLatestBackupLog({
          cluster_id: rowData.cluster.id,
          rollback_time: formData.value.backup_time,
        }),
      ),
    ).then((res) => {
      res.forEach((data, index) => {
        tableData.value[index].backupRecord = data;
        tableData.value[index].backupTime = formData.value.backup_time;
      });
    });
  };

  watch(backupTime, () => {
    emits('change');
  });

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id && backupTime.value) {
        handleDateChange(backupTime.value);
      }
    },
  );

  defineExpose<Exposes>({
    flush() {
      setTimeout(() => {
        const targetRow: {
          backupTime: string;
          rowIndex: number;
        }[] = [];
        const taskList: Promise<SqlserverBackupLogModel>[] = [];
        tableData.value.forEach((rowData, rowIndex) => {
          if (rowData.cluster.id) {
            targetRow.push({
              backupTime: rowData.backupTime,
              rowIndex,
            });
            taskList.push(
              queryLatestBackupLog({
                cluster_id: rowData.cluster.id,
                rollback_time: rowData.backupTime,
              }),
            );
          }
        });

        Promise.all(taskList).then((res) => {
          res.forEach((data, index) => {
            const { backupTime, rowIndex } = targetRow[index];
            tableData.value[rowIndex].backupRecord = data;
            tableData.value[rowIndex].backupTime = backupTime;
          });
        });
      }, 1000);
    },
  });
</script>
<style lang="less" scoped>
  .batch-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .content-block {
    display: grid;
    font-family: MicrosoftYaHei, sans-serif;
    line-height: 24px;
    grid-template-columns: 0fr 1fr;

    .content-label {
      width: 80px;
      text-align: right;
    }

    .content-value {
      width: 200px;
    }
  }

  .content-icon {
    position: absolute;
    top: 50%;
    right: 0;
  }
</style>
