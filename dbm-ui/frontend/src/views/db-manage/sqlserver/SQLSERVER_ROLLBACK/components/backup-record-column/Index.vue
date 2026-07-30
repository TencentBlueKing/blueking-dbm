<template>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="backupRecord"
    :label="t('备份记录')"
    :min-width="370"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('备份记录')"
        title-prefix-type="select"
        :width="504"
        @change="handleBatchEdit">
        <template #content>
          <DbForm
            form-type="vertical"
            :model="formData">
            <BkFormItem
              field="backup_time"
              :label="t('备份文件（批量编辑仅支持“指定时间自动匹配”）')"
              required>
              <BkDatePicker
                v-model="formData.backup_time"
                :clearable="false"
                :disabled-date="disableDate"
                :placeholder="t('请选择')"
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
    <EditableBlock
      v-if="modelValue?.backup_id"
      style="width: 100%"
      @click="handleShowSelector">
      <div class="content-block">
        <div class="content-label">{{ t('备份记录 ：') }}</div>
        <div class="content-value">{{ utcDisplayTime(modelValue.end_time) }}</div>
        <div class="content-label">{{ t('备份角色 ：') }}</div>
        <div class="content-value">
          {{ modelValue.role }}
        </div>
        <div class="content-label">{{ t('备份 ID ：') }}</div>
        <div class="content-value">
          {{ modelValue.backup_id || '--' }}
        </div>
        <div class="content-label">{{ t('备份包含库 ：') }}</div>
        <div class="content-value">
          <BackupDbTags :list="modelValue.backup_db_list" />
        </div>
        <div class="content-label">{{ t('备份缺失库 ：') }}</div>
        <div class="content-value">
          <BackupDbTags
            :list="modelValue.excluded_db_list"
            theme="warning" />
        </div>
        <div class="content-label">{{ t('数据库大小 ：') }}</div>
        <div class="content-value">{{ bytePretty((modelValue.backup_db_size_kb ?? 0) * 1024) }}</div>
        <div class="content-label">{{ t('备份文件大小 ：') }}</div>
        <div class="content-value">{{ bytePretty(modelValue.backup_file_size_kb * 1024) }}</div>
        <div
          v-if="modelValue.bill_id"
          class="content-label">
          {{ t('关联单据 ：') }}
        </div>
        <div
          v-if="modelValue.bill_id"
          class="content-value">
          <RouterLink
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: modelValue.bill_id,
              },
            }">
            {{ modelValue.bill_id }}
          </RouterLink>
        </div>
      </div>
      <DbIcon
        class="content-icon"
        type="down-big" />
    </EditableBlock>
    <EditableSelect
      v-else
      :popover-options="{
        boundary: 'parent',
        trigger: 'manual',
        isShow: false,
      }"
      @click="handleShowSelector" />
  </EditableColumn>
  <BackupRecordSelector
    v-model="modelValue"
    v-model:is-show="isShowSelector"
    v-bind="props" />
</template>
<script lang="ts" setup>
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import SqlserverBackupLogModel from '@services/model/sqlserver/backup-log';
  import { queryLatestBackupLog } from '@services/source/sqlserver';

  import { useTimeZoneFormat } from '@hooks';

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

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<SqlserverBackupLogModel | undefined>({
    required: true,
  });

  const tableData = defineModel<
    {
      backupRecord: SqlserverBackupLogModel | undefined;
      cluster: Props['cluster'];
    }[]
  >('tableData', {
    required: true,
  });

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const isShowSelector = ref(false);
  const isShowBatchEdit = ref(false);

  const formData = ref({
    backup_time: '',
  });

  const disabledMethod = () => (props.cluster.id ? false : t('请先选择集群'));
  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEdit = () => {
    Promise.all(
      tableData.value.map((rowData) =>
        queryLatestBackupLog({
          cluster_id: rowData.cluster.id,
          rollback_time: formatDateToUTC(formData.value.backup_time),
        }),
      ),
    ).then((res) => {
      res.forEach((data, index) => {
        tableData.value[index].backupRecord = data;
      });
    });
  };

  watch(modelValue, () => {
    emits('change');
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
    grid-template-columns: 0fr 1fr;
    font-family: MicrosoftYaHei, sans-serif;
    line-height: 24px;

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
