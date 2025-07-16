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
      :title="t('DB 重命名：database 重命名')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            ref="clusterRef"
            v-model="item.cluster"
            allows-duplicates
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <DbNameColumn
            v-model="item.fromDatabase"
            :allow-wildcard="false"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="fromDatabase"
            :label="t('源 DB 名')"
            required
            :rules="rules.fromDatabase"
            single
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.toDatabase"
            check-exist
            :cluster-id="item.cluster.id"
            field="toDatabase"
            :label="t('新 DB 名')"
            required
            :rules="rules.toDatabase"
            single
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <BkFormItem
        v-bk-tooltips="t('存在业务连接时需要人工确认')"
        class="fit-content">
        <BkCheckbox
          v-model="formData.force"
          :false-label="false"
          true-label>
          <span class="safe-action-text">{{ t('检查业务连接') }}</span>
        </BkCheckbox>
      </BkFormItem>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/db-name-column/Index.vue';

  interface RowData {
    cluster: TendbClusterModel;
    fromDatabase: string[];
    toDatabase: string[];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const clusterRef = ref<InstanceType<typeof ClusterColumn>[]>();
  const tableKey = ref(Date.now());

  const batchInputConfig = [
    {
      case: 'spider.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'db1',
      key: 'fromDatabase',
      label: t('源 DB 名'),
    },
    {
      case: 'db2',
      key: 'toDatabase',
      label: t('新 DB 名'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster:
      data.cluster ||
      ({
        id: 0,
        master_domain: '',
      } as TendbClusterModel),
    fromDatabase: data.fromDatabase || [],
    toDatabase: data.toDatabase || [],
  });

  const defaultData = () => ({
    force: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() => ({
    [ClusterTypes.TENDBCLUSTER]: formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster),
  }));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );
  const dbNameCheckMap = computed(() =>
    formData.tableData.reduce<Record<string, number>>((acc, item) => {
      const domain = item.cluster.master_domain;
      const fromDatabase = item.fromDatabase[0] || '';
      const toDatabase = item.toDatabase[0] || '';
      if (!domain) {
        return acc;
      }
      Object.assign(acc, {
        [`${domain}/${fromDatabase}`]: (acc[`${domain}/${fromDatabase}`] || 0) + 1,
        [`${domain}/${toDatabase}`]: (acc[`${domain}/${toDatabase}`] || 0) + 1,
      });
      return acc;
    }, {}),
  );

  const validator = async (value: string[], { rowData }: Record<string, any>) => {
    if (!value.length) {
      return true;
    }
    await nextTick();
    const domain = (rowData as RowData).cluster.master_domain;
    if (!domain) {
      return true;
    }
    return _.every(value, (item) => dbNameCheckMap.value[`${domain}/${item}`] <= 1);
  };

  const rules = {
    fromDatabase: [
      {
        message: t('同集群其他单元格出现重复的 DB 名'),
        trigger: 'blur',
        validator,
      },
      {
        message: t('同集群其他单元格出现重复的 DB 名'),
        trigger: 'change',
        validator,
      },
    ],
    toDatabase: [
      {
        message: t('同集群其他单元格出现重复的 DB 名'),
        trigger: 'blur',
        validator,
      },
      {
        message: t('同集群其他单元格出现重复的 DB 名'),
        trigger: 'change',
        validator,
      },
    ],
  };

  useTicketDetail<TendbCluster.RenameDataBase>(TicketTypes.TENDBCLUSTER_RENAME_DATABASE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, force } = details;
      Object.assign(formData, {
        force,
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) => ({
          cluster: {
            id: item.cluster_id,
            master_domain: clusters[item.cluster_id].immute_domain,
          },
          fromDatabase: item.from_database ? [item.from_database] : [],
          toDatabase: item.to_database ? [item.to_database] : [],
        })),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    force: boolean;
    infos: {
      cluster_id: number;
      from_database: string;
      to_database: string;
    }[];
  }>(TicketTypes.TENDBCLUSTER_RENAME_DATABASE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        force: formData.force,
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          from_database: item.fromDatabase[0],
          to_database: item.toDatabase[0],
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbClusterModel[]) => {
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
        cluster: {
          master_domain: item.master_domain,
        } as TendbClusterModel,
        fromDatabase: item.fromDatabase ? [item.fromDatabase] : [],
        toDatabase: item.toDatabase ? [item.toDatabase] : [],
      }),
    );
    if (isClear) {
      tableKey.value = Date.now();
      formData.tableData = [...dataList]; // 覆盖
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList]; // 追加
    }
    setTimeout(() => {
      formData.tableData.forEach((item, index) => {
        clusterRef.value?.[index]
          ?.fetch?.({
            exact_domain: item.cluster.master_domain,
          })
          .then(() => {
            tableRef.value?.validateByRowIndex(index);
          });
      });
    });
  };
</script>
