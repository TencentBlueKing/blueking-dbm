<template>
  <div class="tendbcluster-toolbox-record-flashback-page">
    <SmartAction>
      <BkAlert
        class="mb-10"
        closable
        theme="info"
        :title="t('闪回：通过 flashback 工具，对 row 格式的 binlog 做逆向操作')" />
      <BkForm
        ref="formRef"
        class="mb-24"
        form-type="vertical">
        <BkFormItem
          :label="t('时区')"
          required>
          <TimeZonePicker style="width: 450px" />
        </BkFormItem>
        <BkFormItem
          :label="t('闪回方式')"
          required>
          <BkRadioGroup
            v-model="formData.flashback_type"
            @change="handleFlashbackTypeChange">
            <BkRadioButton
              label="TABLE_FLASHBACK"
              style="width: 225px">
              {{ t('库表闪回') }}
            </BkRadioButton>
            <BkRadioButton
              label="RECORD_FLASHBACK"
              style="width: 225px">
              {{ t('记录级闪回') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <EditableTable
          ref="editableTableRef"
          :model="tableData">
          <EditableTableRow
            v-for="(rowData, index) in tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :selected-ids="selectedClusterIds"
              @batch-edit="handleBatchEdit" />
            <DatetimeColumn
              v-model="rowData.start_time"
              field="start_time"
              :label="t('回档时间')" />
            <DatetimeColumn
              v-model="rowData.end_time"
              :disabled-date="(date) => handleEditTimeDisableCallback(date, rowData.start_time)"
              field="end_time"
              :label="t('截止时间')"
              nowenable />
            <DbNameColumn
              v-model="rowData.databases"
              :cluster-id="rowData.cluster?.id" />
            <TableNameColumn
              v-model="rowData.tables"
              :cluster-id="rowData.cluster?.id"
              :label="t('目标表')" />
            <RecordColumn
              v-model="rowData.rows_filter"
              :cluster-id="rowData.cluster?.id" />
            <OperationColumn
              v-model:table-data="tableData"
              :create-row-method="createTableData" />
          </EditableTableRow>
        </EditableTable>
        <BkFormItem class="mt-20">
          <BkCheckbox
            v-model="formData.direct_write_back"
            :false-label="false"
            true-label>
            {{ t('覆盖原始数据') }}
          </BkCheckbox>
        </BkFormItem>
        <BkFormItem :label="t('备注')">
          <BkInput
            :rows="3"
            style="max-width: 1000px"
            type="textarea" />
        </BkFormItem>
      </BkForm>
      <template #action>
        <BkButton
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton class="ml-8">{{ t('重置') }}</BkButton>
      </template>
    </SmartAction>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { createTicket, getTicketDetails } from '@services/source/ticket';

  import { useTimeZoneFormat } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import DatetimeColumn from './components/DatetimeColumn.vue';
  import DbNameColumn from './components/DbNameColumn.vue';
  import OperationColumn from './components/OperationColumn.vue';
  import RecordColumn from './components/RecordColumn.vue';
  import TableNameColumn from './components/TableNameColumn.vue';

  interface IRowData {
    cluster?: {
      id?: number;
      master_domain?: string;
    };
    databases?: string[];
    direct_write_back?: boolean;
    end_time?: string;
    rows_filter?: string;
    start_time?: string;
    tables?: string[];
  }

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const createTableData = (data = {} as IRowData) => ({
    cluster: data.cluster,
    databases: data.databases || [],
    direct_write_back: data.direct_write_back || false,
    end_time: data.end_time || '',
    rows_filter: data.rows_filter || '',
    start_time: data.start_time || '',
    tables: data.tables || [],
  });

  const formRef = useTemplateRef('formRef');
  const editableTableRef = useTemplateRef('editableTableRef');
  const tableData = ref([createTableData()]);

  const isSubmiting = ref(false);
  const formData = reactive({
    direct_write_back: true,
    flashback_type: 'RECORD_FLASHBACK',
    remark: '',
  });

  if (Number(route.query.ticketId)) {
    getTicketDetails<TicketModel<TendbCluster.FlashBack>>({
      id: Number(route.query.ticketId),
    }).then((data) => {
      formData.flashback_type = data.details.flashback_type;
      formData.remark = data.remark;
      formData.direct_write_back = data.details.infos[0].direct_write_back;
      tableData.value = data.details.infos.map((item) =>
        createTableData({
          ...item,
          cluster: {
            id: item.cluster_id,
            master_domain: data.details.clusters[item.cluster_id].immute_domain,
          },
        }),
      );
    });
  }

  const selectedClusterIds = computed(() =>
    _.filter(
      tableData.value.map((item) => item.cluster?.id || 0),
      (item) => Number(item) > 0,
    ),
  );

  const handleFlashbackTypeChange = (type: string) => {
    if (type === 'TABLE_FLASHBACK') {
      router.push({
        name: 'spiderFlashback',
      });
    }
  };

  const handleEditTimeDisableCallback = (date: Date | number, startDate: string) =>
    dayjs(date).isBefore(dayjs(startDate));

  const handleBatchEdit = (list: TendbclusterModel[]) => {
    const dataList = list.reduce<ReturnType<typeof createTableData>[]>((acc, item) => {
      if (!selectedClusterIds.value.includes(item.id)) {
        acc.push(
          createTableData({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selectedClusterIds.value.length ? tableData.value : []), ...dataList];
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    Promise.all([formRef.value!.validate(), editableTableRef.value!.validate()])
      .then(() =>
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            flashback_type: 'RECORD_FLASHBACK',
            force: true,
            infos: tableData.value.map((item) => ({
              cluster_id: item.cluster?.id,
              databases: item.databases,
              databases_ignore: [],
              direct_write_back: formData.direct_write_back,
              end_time: formatDateToUTC(item.end_time),
              rows_filter: item.rows_filter,
              start_time: formatDateToUTC(item.start_time),
              tables: item.tables,
              tables_ignore: [],
            })),
          },
          remark: formData.remark,
          ticket_type: TicketTypes.TENDBCLUSTER_FLASHBACK,
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'spiderFlashback',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        }),
      )
      .finally(() => {
        isSubmiting.value = false;
      });
  };
</script>
<style lang="less">
  .tendbcluster-toolbox-record-flashback-page {
    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
