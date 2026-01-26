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
      :title="t('DB 克隆：将源集群的指定database表结构和数据完整克隆到新集群中， database名不变')" />
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
            v-model="item.source_cluster"
            allow-repeat
            field="source_cluster.master_domain"
            :label="t('源集群')"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <DataSchemaGrantColumn
            v-model="item.data_schema_grant"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.clone_db_list"
            check-not-exist
            :cluster-id="item.source_cluster?.id"
            field="clone_db_list"
            :label="t('克隆 DB 名')"
            required
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_db_list"
            :cluster-id="item.source_cluster?.id"
            field="ignore_db_list"
            :label="t('忽略 DB')"
            @batch-edit="handleBatchEdit" />
          <TargetClusterColumn
            v-model="item.target_clusters"
            :cluster="item.source_cluster" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
    <template #action>
      <BkButton
        class="mr-16 w-88"
        @click="handleAssessment">
        {{ t('磁盘空间评估') }}
      </BkButton>
      <BkButton
        class="mr-8 w-88"
        :disabled="!assessmentValidate || isSubmitting"
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
  <Assessment
    ref="assessmentRef"
    v-model:table-data="formData.tableData"
    @request-success="handleAssessmentSuccess" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';

  import { random } from '@utils';

  import Assessment from './components/assessment/Index.vue';
  import DataSchemaGrantColumn from './components/DataSchemaGrantColumn.vue';
  import TargetClusterColumn from './components/TargetClusterColumn.vue';

  interface RowData {
    clone_db_list: string[];
    data_schema_grant: string;
    db_list: string[];
    ignore_db_list: string[];
    source_cluster: TendbhaModel;
    target_clusters: TendbhaModel[];
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'source_master_domain',
      label: t('源集群'),
    },
    {
      case: '表结构和数据',
      key: 'data_schema_grant',
      label: t('克隆类型'),
    },
    {
      case: '*',
      key: 'clone_db_list',
      label: t('克隆 DB 名'),
    },
    {
      case: 'NULL',
      key: 'ignore_db_list',
      label: t('忽略 DB'),
    },
    {
      case: 'tendbha2.test.dba.db,tendbha3.test.dba.db',
      key: 'target_master_domain',
      label: t('目标集群'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    clone_db_list: data.clone_db_list || [],
    data_schema_grant: data.data_schema_grant || '',
    db_list: data.db_list || [],
    ignore_db_list: data.ignore_db_list || [],
    source_cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.source_cluster,
    ),
    target_clusters: data.target_clusters || [],
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const assessmentRef = ref<InstanceType<typeof Assessment>>();
  const assessmentValidate = ref(false);

  const selected = computed(() =>
    formData.tableData.filter((item) => item.source_cluster.id).map((item) => item.source_cluster),
  );
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.source_cluster.master_domain, true])),
  );

  useTicketDetail<Mysql.DataMigrate>(TicketTypes.MYSQL_DATA_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => ({
          clone_db_list: item.clone_db_list,
          data_schema_grant: item.data_schema_grant,
          db_list: item.db_list,
          ignore_db_list: item.ignore_db_list,
          source_cluster: {
            master_domain: clusters[item.source_cluster].immute_domain || '',
          },
          target_clusters: item.target_clusters.map((clusterId) => ({
            cluster_type: clusters[clusterId].cluster_type || '',
            id: clusters[clusterId].id || 0,
            master_domain: clusters[clusterId].immute_domain || '',
          })),
        })),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      clone_db_list: string[];
      data_schema_grant: string;
      db_list: string[];
      ignore_db_list: string[];
      source_cluster: number;
    }[];
  }>(TicketTypes.MYSQL_DATA_MIGRATE);

  watch(
    () => formData.tableData,
    () => {
      assessmentValidate.value = false;
    },
    { deep: true },
  );

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          clone_db_list: item.clone_db_list,
          data_schema_grant: item.data_schema_grant,
          db_list: item.db_list,
          ignore_db_list: item.ignore_db_list,
          source_cluster: item.source_cluster.id,
          target_clusters: item.target_clusters.map((cluster) => cluster.id),
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
    assessmentRef.value?.reset();
  };

  const handleAssessment = async () => {
    const result = await tableRef.value?.validate();
    if (!result) {
      return;
    }
    assessmentRef.value?.run();
  };

  const handleAssessmentSuccess = (validate: boolean) => {
    assessmentValidate.value = validate;
  };

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            source_cluster: cluster,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const cloneTypeMap = {
      [t('表结构')]: 'schema',
      [t('表结构和数据')]: 'data,schema',
    };
    const dataList = data.map((item) =>
      createTableRow({
        clone_db_list: item.clone_db_list ? item.clone_db_list.split(',') : [],
        data_schema_grant: cloneTypeMap[item.data_schema_grant] || '',
        ignore_db_list: item.ignore_db_list ? item.ignore_db_list.split(',') : [],
        source_cluster: {
          master_domain: item.source_master_domain,
        } as TendbhaModel,
        target_clusters: (item.target_master_domain?.split(',') || []).map((item: string) => ({
          master_domain: item,
        })),
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList];
    }

    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };
</script>
