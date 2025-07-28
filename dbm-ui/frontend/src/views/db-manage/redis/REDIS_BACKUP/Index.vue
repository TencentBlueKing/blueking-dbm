<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mb-24"
          :model="formData.tableData">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('架构版本')"
              :width="300">
              <EditableBlock
                v-model="rowData.cluster.cluster_type_name"
                :placeholder="t('自动生成')">
              </EditableBlock>
            </EditableColumn>
            <TargetColumn
              v-model="rowData.target"
              @batch-edit="handleBatchEdit">
            </TargetColumn>
            <BackupTypeColumn
              v-model="rowData.backup_type"
              @batch-edit="handleBatchEdit">
            </BackupTypeColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="ml-8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import BackupTypeColumn, { BackupType } from './components/BackupTypeColumn.vue';
  import ClusterColumn from './components/ClusterColumn.vue';
  import TargetColumn from './components/TargetColumn.vue';

  interface IDataRow {
    backup_type: string;
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    target: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    backup_type: values.backup_type || BackupType.NORMAL_BACKUP,
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    target: values.target || 'slave',
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
    type: TicketTypes.REDIS_BACKUP,
  });

  const { t } = useI18n();
  const route = useRoute();

  useTicketDetail<Redis.Backup>(TicketTypes.REDIS_BACKUP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.rules.map((item) =>
          createRowData({
            backup_type: item.backup_type,
            cluster: {
              master_domain: item.domain,
            } as IDataRow['cluster'],
            target: item.target,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    rules: {
      backup_type: string;
      cluster_id: number;
      domain: string;
      target: string;
    }[];
  }>(TicketTypes.REDIS_BACKUP);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  // 集群列表跳转
  const { masterDomain } = route.query as { masterDomain: string };
  if (masterDomain) {
    const domainList = masterDomain.split(',');
    Object.assign(formData, {
      tableData: domainList.map((domain) =>
        createRowData({
          cluster: {
            master_domain: domain,
          } as IDataRow['cluster'],
        }),
      ),
    });
  }

  const selected = computed(() =>
    formData.tableData.filter((item) => item.cluster.master_domain).map((item) => item.cluster),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          rules: formData.tableData.map((item) => ({
            backup_type: item.backup_type,
            cluster_id: item.cluster.id,
            domain: item.cluster.master_domain,
            target: item.target,
          })),
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>
