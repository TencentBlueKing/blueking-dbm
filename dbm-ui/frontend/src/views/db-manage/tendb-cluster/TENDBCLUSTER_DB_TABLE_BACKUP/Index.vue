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
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('指定库表备份_支持模糊匹配')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16 toolbox-form"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            allow-repeat
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <BackupLocalColumn
            v-model="item.backup_local"
            :cluster="item.cluster"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.db_patterns"
            :cluster-id="item.cluster?.id"
            field="db_patterns"
            :label="t('备份 DB 名')"
            required
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_dbs"
            :cluster-id="item.cluster?.id"
            field="ignore_dbs"
            :label="t('忽略 DB 名')"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.table_patterns"
            :cluster-id="item.cluster?.id"
            field="table_patterns"
            :label="t('备份表名')"
            required
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.ignore_tables"
            :cluster-id="item.cluster?.id"
            field="ignore_tables"
            :label="t('忽略表名')"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import BackupLocalColumn from './components/BackupLocalColumn.vue';

  interface RowData {
    backup_local: string;
    cluster: TendbclusterModel;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '192.168.10.2:20000',
      key: 'backup_local',
      label: t('备份位置'),
    },
    {
      case: '*',
      key: 'db_patterns',
      label: t('备份 DB 名'),
    },
    {
      case: 'NULL',
      key: 'ignore_dbs',
      label: t('忽略 DB 名'),
    },
    {
      case: '*',
      key: 'table_patterns',
      label: t('备份表名'),
    },
    {
      case: 'NULL',
      key: 'ignore_tables',
      label: t('忽略表名'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    backup_local: data.backup_local || '',
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbclusterModel,
      data.cluster,
    ),
    db_patterns: data.db_patterns || ['*'],
    ignore_dbs: data.ignore_dbs || [],
    ignore_tables: data.ignore_tables || [],
    table_patterns: data.table_patterns || ['*'],
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  useTicketDetail<TendbCluster.DbTableBackup>(TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => ({
          backup_local: item.spider_mnt_address ? `spider_mnt::${item.spider_mnt_address}` : item.backup_local,
          cluster: {
            master_domain: clusters[item.cluster_id].immute_domain,
          },
          db_patterns: item.db_patterns,
          ignore_dbs: item.ignore_dbs,
          ignore_tables: item.ignore_tables,
          table_patterns: item.table_patterns,
        })),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      backup_local: string;
      cluster_id: number;
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    }[];
  }>(TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          backup_local: item.backup_local,
          cluster_id: item.cluster.id,
          db_patterns: item.db_patterns,
          ignore_dbs: item.ignore_dbs,
          ignore_tables: item.ignore_tables,
          table_patterns: item.table_patterns,
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbclusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            cluster,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        backup_local: item.backup_local || '',
        cluster: {
          master_domain: item.master_domain,
        } as TendbclusterModel,
        db_patterns: item.db_patterns ? item.db_patterns.split(',') : [],
        ignore_dbs: item.ignore_dbs ? item.ignore_dbs.split(',') : [],
        ignore_tables: item.ignore_tables ? item.ignore_tables.split(',') : [],
        table_patterns: item.table_patterns ? item.table_patterns.split(',') : [],
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };
</script>
