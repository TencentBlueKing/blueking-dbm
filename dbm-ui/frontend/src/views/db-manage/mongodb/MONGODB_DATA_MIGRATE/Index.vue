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
    <div class="mongo-data-migrate-page db-toolbox">
      <BkAlert
        class="mb-16"
        theme="info"
        :title="
          t(
            '数据迁移：将源用户库迁入已存在的空目标。支持 RS↔RS、分片↔分片、分片→RS、RS→分片；RS→分片需用户预先在目标上 shardCollection。数据源可为在线集群或备份单据',
          )
        " />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <EditableColumn
              field="source_mode"
              :label="t('数据源')"
              :min-width="160"
              required>
              <BkSelect
                v-model="item.source_mode"
                :clearable="false">
                <BkOption
                  :label="t('在线集群')"
                  value="cluster" />
                <BkOption
                  :label="t('备份单据')"
                  value="backup_ticket" />
              </BkSelect>
            </EditableColumn>
            <ClusterColumn
              v-model="item.source_cluster"
              :label="t('源集群')"
              field="source_cluster.master_domain"
              :selected="selectedSources"
              @batch-edit="handleSourceBatchEdit" />
            <BackupTicketColumn
              v-model="item.backup_ticket_id"
              :required="item.source_mode === 'backup_ticket'"
              :source-cluster="item.source_cluster" />
            <TargetClusterColumn
              v-model="item.target_cluster"
              :selected="selectedTargets"
              :source-cluster="item.source_cluster"
              @batch-edit="handleTargetBatchEdit" />
            <DbNameColumn
              v-model="item.db_patterns"
              :cluster-id="item.source_cluster.id"
              field="db_patterns"
              :label="t('DB 名')"
              @batch-edit="handleDbTableBatchEdit" />
            <DbNameColumn
              v-model="item.ignore_dbs"
              :cluster-id="item.source_cluster.id"
              field="ignore_dbs"
              :label="t('忽略DB名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <TableNameColumn
              v-model="item.table_patterns"
              field="table_patterns"
              :label="t('表名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <TableNameColumn
              v-model="item.ignore_tables"
              field="ignore_tables"
              :label="t('忽略表名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mongodb/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mongodb/common/toolbox-field/table-name-column/Index.vue';

  import { random } from '@utils';

  import BackupTicketColumn from './components/BackupTicketColumn.vue';
  import TargetClusterColumn from './components/TargetClusterColumn.vue';

  interface IDataRow {
    backup_ticket_id?: number;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    source_cluster: {
      cluster_type: ClusterTypes | string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    source_mode: 'backup_ticket' | 'cluster';
    table_patterns: string[];
    target_cluster: {
      cluster_type: ClusterTypes | string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    backup_ticket_id: values.backup_ticket_id,
    db_patterns: values.db_patterns || [],
    ignore_dbs: values.ignore_dbs || [],
    ignore_tables: values.ignore_tables || [],
    source_cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.source_cluster,
    ),
    source_mode: values.source_mode || ('cluster' as const),
    table_patterns: values.table_patterns || [],
    target_cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.target_cluster,
    ),
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.DataMigrate>(TicketTypes.MONGODB_DATA_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((item) =>
          createRowData({
            backup_ticket_id: item.backup_ticket_id,
            db_patterns: item.ns_filter?.db_patterns || [],
            ignore_dbs: item.ns_filter?.ignore_dbs || [],
            ignore_tables: item.ns_filter?.ignore_tables || [],
            source_cluster: {
              master_domain: clusters[item.source_cluster_id].immute_domain,
            } as IDataRow['source_cluster'],
            source_mode: item.source_mode,
            table_patterns: item.ns_filter?.table_patterns || [],
            target_cluster: {
              master_domain: clusters[item.target_cluster_id].immute_domain,
            } as IDataRow['target_cluster'],
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Mongodb.DataMigrate['infos'];
  }>(TicketTypes.MONGODB_DATA_MIGRATE);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());
  const formData = reactive(createDefaultFormData());

  const selectedSources = computed(() =>
    formData.tableData.filter((item) => item.source_cluster.id).map((item) => item.source_cluster),
  );
  const selectedTargets = computed(() =>
    formData.tableData.filter((item) => item.target_cluster.id).map((item) => item.target_cluster),
  );
  const selectedSourceMap = computed(() =>
    Object.fromEntries(selectedSources.value.map((cur) => [cur.master_domain, true])),
  );

  const handleSubmit = async () => {
    await formRef.value!.validate();
    editableTableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => {
            const info: Mongodb.DataMigrate['infos'][number] = {
              ns_filter: {
                db_patterns: tableRow.db_patterns,
                ignore_dbs: tableRow.ignore_dbs,
                ignore_tables: tableRow.ignore_tables,
                table_patterns: tableRow.table_patterns,
              },
              source_cluster_id: tableRow.source_cluster.id,
              source_mode: tableRow.source_mode,
              target_cluster_id: tableRow.target_cluster.id,
            };
            if (tableRow.source_mode === 'backup_ticket' && tableRow.backup_ticket_id) {
              info.backup_ticket_id = tableRow.backup_ticket_id;
            }
            return info;
          }),
        },
        ...formData.payload,
      });
    });
  };

  const handleSourceBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedSourceMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            source_cluster: {
              master_domain: item.master_domain,
            } as IDataRow['source_cluster'],
          }),
        );
      }
    });
    formData.tableData = [...(selectedSources.value.length ? formData.tableData : []), ...newList];
  };

  const handleTargetBatchEdit = (clusterList: MongodbModel[]) => {
    if (!clusterList.length) {
      return;
    }
    const firstEmpty = formData.tableData.find((item) => !item.target_cluster.id);
    const cluster = clusterList[0]!;
    if (firstEmpty) {
      firstEmpty.target_cluster = {
        cluster_type: cluster.cluster_type,
        cluster_type_name: cluster.cluster_type_name,
        id: cluster.id,
        master_domain: cluster.master_domain,
      };
      return;
    }
    formData.tableData.push(
      createRowData({
        target_cluster: {
          cluster_type: cluster.cluster_type,
          cluster_type_name: cluster.cluster_type_name,
          id: cluster.id,
          master_domain: cluster.master_domain,
        },
      }),
    );
  };

  const handleDbTableBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>

<style lang="less" scoped>
  .mongo-data-migrate-page {
    padding-bottom: 20px;
  }
</style>
