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
  <SmartAction>
    <div class="oracle-sql-execute-page">
      <BkAlert
        closable
        theme="info"
        :title="t('提供多个集群批量执行sql文件功能')" />
      <DbForm
        ref="formRef"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <DbNameColumn
              v-model="rowData.execute_db"
              @batch-edit="handleColumnBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <SqlItem
          :key="resetFormKey"
          ref="sqlItemRef"
          v-model="formData.script_files"
          v-model:import-mode="formData.importMode"
          :cluster-version-list="clusterVersionList" />
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import OracalHaModel from '@services/model/oracle/oracle-ha';
  import type { Oracle } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { useSqlImport } from '@stores';

  import { DBTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import DbNameColumn from './components/DbNameColumn.vue';
  import SqlItem from './components/sql-item/Index.vue';

  interface IDataRow {
    cluster: {
      cluster_type: string;
      id: number;
      major_version: string;
      master_domain: string;
    };
    execute_db: string[];
  }

  const route = useRoute();
  const { t } = useI18n();
  const { updateDbType, updateUploadFilePath } = useSqlImport();

  updateDbType(DBTypes.ORACLE);

  useTicketDetail<Oracle.ImportSqlFile>(TicketTypes.ORACLE_EXEC_SCRIPT_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        importMode: details.import_mode,
        payload: createTickePayload(ticketDetail),
        script_files: details.script_files,
        tableData: details.cluster_info.map((item) =>
          createRowData({
            cluster: {
              master_domain: details.clusters[item.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            execute_db: item.execute_db,
          }),
        ),
      });
      updateUploadFilePath(details.path);
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_info: {
      cluster_id: number;
      execute_db: string[];
    }[];
    import_mode: string;
    script_files: string[];
  }>(TicketTypes.ORACLE_EXEC_SCRIPT_APPLY);

  const createDefaultData = () => ({
    importMode: 'manual' as 'manual' | 'file',
    payload: createTickePayload(),
    script_files: [] as string[],
    tableData: [createRowData()],
  });

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        major_version: '',
        master_domain: '',
      },
      values.cluster,
    ),
    execute_db: values.execute_db || [],
  });

  const formRef = useTemplateRef('formRef');
  const editableTableRef = useTemplateRef('editableTable');
  const sqlItemRef = useTemplateRef('sqlItemRef');

  const resetFormKey = ref(0);

  const formData = reactive(createDefaultData());

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

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));
  const clusterVersionList = computed(() => selected.value.map((item) => item.major_version));

  const handleClusterBatchEdit = (clusterList: OracalHaModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleColumnBatchEdit = (value: string[] | string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = () => {
    Promise.all([formRef.value!.validate(), editableTableRef.value!.validate(), sqlItemRef.value!.getValue()]).then(
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      ([formValue, tableValue, sqlItemValue]) => {
        if (tableValue) {
          createTicketRun({
            details: {
              cluster_info: formData.tableData.map((tableItem) => ({
                cluster_id: tableItem.cluster.id,
                execute_db: tableItem.execute_db,
              })),
              import_mode: formData.importMode,
              ...sqlItemValue,
            },
            ...formData.payload,
          });
        }
      },
    );
  };

  const handleReset = () => {
    resetFormKey.value = resetFormKey.value + 1;
    Object.assign(formData, createDefaultData());
  };
</script>

<style lang="less">
  .oracle-sql-execute-page {
    padding-bottom: 40px;

    .bk-form-label {
      font-weight: bold;
      color: #313238;

      &::after {
        line-height: unset !important;
      }
    }
  }
</style>
