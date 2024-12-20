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
    <BkAlert
      class="mb-20"
      closable
      :title="t('添加运维节点：在原集群上增加运维节点实例来实现额外的数据访问，在运维节点上的操作不会影响原集群')" />
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <TendbCluster
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit"
            @change="(data) => handleChange(data, item)" />
          <Column
            field="cloud.id"
            :label="t('所属管控区域')"
            :min-width="300">
            <Block
              v-model="item.cloud.name"
              :placeholder="t('自动生成')" />
          </Column>
          <MultipleHost
            v-model="item.host"
            field="host"
            :label="t('运维节点 IP')" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <TicketRemark v-model="formData.remark" />
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { filterClusters } from '@services/source/dbbase';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';
  import TicketRemark from '@components/ticket-remark/TicketRemark.vue';

  import MultipleHost from '@views/db-manage/common/toolbox-field/host-column/MultipleHost.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TendbCluster from '@views/db-manage/tendb-cluster/common/edit-table-column/TendbCluster.vue';

  interface RowData {
    cluster: {
      id: number;
      domain: string;
    };
    cloud: {
      id: number;
      name: string;
    };
    host: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      domain: '',
    },
    cloud: data.cloud || {
      id: 0,
      name: '',
    },
    host: data.host || [],
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.domain, true])));

  const rules = {
    'cluster.domain': [
      {
        validator: (value: string) => selected.value.filter((item) => item.domain === value).length < 2,
        message: t('目标集群重复'),
        trigger: 'change',
      },
    ],
  };

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      bk_cloud_id: number;
      cluster_id: number;
      resource_spec: {
        spider_ip_list: {
          spec_id: number;
          hosts: {
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
        };
      };
    }[];
  }>(TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    console.log(formData.tableData, 'formData.tableData');
    createTicketRun(
      {
        infos: formData.tableData.map((item) => ({
          bk_cloud_id: item.cloud.id,
          cluster_id: item.cluster.id,
          resource_spec: {
            spider_ip_list: {
              spec_id: 0,
              hosts: item.host,
            },
          },
        })),
      },
      formData.remark,
    );
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              id: item.id,
              domain: item.master_domain,
            },
            cloud: {
              id: item.bk_cloud_id,
              name: item.bk_cloud_name,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleChange = (data: ServiceReturnType<typeof filterClusters>[number], row: RowData) => {
    row.cloud = {
      id: data.bk_cloud_id,
      name: data.bk_cloud_name,
    };
  };
</script>
