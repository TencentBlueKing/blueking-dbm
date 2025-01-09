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
      :title="t('扩容接入层：增加集群的Proxy数量')" />
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <Column
            field="cluster.role"
            :label="t('扩容节点类型')"
            :min-width="200"
            required>
            <Select
              v-model="item.cluster.role"
              :input-search="false"
              :list="getNodeTypeOptions(item.cluster)" />
          </Column>
          <SpecColumn
            v-model="item.specId"
            :cluster="item.cluster" />
          <Column
            field="hostType"
            :label="t('主机选择方式')"
            :min-width="200">
            <Select
              v-model="item.hostType"
              :list="hostTypeOptions" />
          </Column>
          <Column
            field="count"
            :label="t('扩容数量（台）')"
            :min-width="200"
            required>
            <Input
              v-model="item.count"
              :max="37 - item.cluster.mnt_count"
              :min="1"
              type="number" />
          </Column>
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

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Column, Input, Row as EditableTableRow, Select } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import SpecColumn from './components/spec-column/Index.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
      bk_cloud_id: number;
      role: string;
      master_spec_ids: number[];
      slave_spec_ids: number[];
      mnt_count: number;
    };
    specId: number;
    hostType: string;
    count: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
      bk_cloud_id: 0,
      role: '',
      master_spec_ids: [],
      slave_spec_ids: [],
      mnt_count: 0,
    },
    specId: data.specId || 0,
    hostType: data.cluster ? 'auto' : '',
    count: data.count || '',
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const hostTypeOptions = [
    {
      label: t('资源池自动匹配'),
      value: 'auto',
    },
  ];

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    ip_source: 'resource_pool';
    infos: {
      cluster_id: number;
      add_spider_role: string;
      resource_spec: {
        spider_ip_list: {
          spec_id: number;
          count: number;
        };
      };
    }[];
  }>(TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        ip_source: 'resource_pool',
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          add_spider_role: item.cluster.role,
          resource_spec: {
            spider_ip_list: {
              spec_id: item.specId,
              count: Number(item.count),
            },
          },
        })),
      },
      remark: formData.remark,
    });
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
              master_domain: item.master_domain,
              bk_cloud_id: item.bk_cloud_id,
              role:
                // eslint-disable-next-line no-nested-ternary
                item.spider_master.length > 0 ? 'spider_master' : item.spider_slave.length > 0 ? 'spider_slave' : '',
              master_spec_ids: item.spider_master.map((item) => item.spec_config?.id),
              slave_spec_ids: item.spider_slave.map((item) => item.spec_config?.id),
              mnt_count: item.spider_mnt.length,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const getNodeTypeOptions = (cluster: RowData['cluster']) => {
    const list = [];
    if (cluster.master_spec_ids.length) {
      list.push({
        value: 'spider_master',
        label: 'Master',
      });
    }
    if (cluster.slave_spec_ids.length) {
      list.push({
        value: 'spider_slave',
        label: 'Slave',
      });
    }
    return list;
  };
</script>
