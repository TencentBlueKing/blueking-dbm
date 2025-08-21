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
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-20"
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
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <RoleColumn
            v-model="item.role"
            :cluster="item.cluster" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :current-spec-id-list="
              item.role === 'spider_slave' ? item.cluster.spider_slave_spec_list : item.cluster.spider_master_spec_list
            "
            :machine-type="
              item.role === 'spider_slave' ? MachineTypes.TENDBCLUSTER_BACKEND : MachineTypes.TENDBCLUSTER_PROXY
            "
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <EditableColumn
            field="count"
            :label="t('扩容数量（台）')"
            :min-width="150"
            required>
            <EditableInput
              v-model="item.count"
              :max="37 - item.cluster.mnt_count"
              :min="1"
              type="number" />
          </EditableColumn>
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.cluster.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import ClusterColumn from './components/ClusterColumn.vue';
  import RoleColumn from './components/RoleColumn.vue';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    count: string;
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    role: string;
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'spider.tendb-test.1.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'spider_slave',
      key: 'role',
      label: t('扩容节点类型'),
    },
    {
      case: '通用proxy配置',
      key: 'spec_name',
      label: t('规格'),
    },
    {
      case: '1',
      key: 'count',
      label: t('扩容数量（台）'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        id: 0,
        master_domain: '',
        mnt_count: 0,
        region: '',
        spider_master: [] as TendbClusterModel['spider_master'],
        spider_master_spec_list: [] as number[],
        spider_slave: [] as TendbClusterModel['spider_slave'],
        spider_slave_spec_list: [] as number[],
      },
      data.cluster,
    ),
    count: data.count || '',
    labels: (data.labels || []) as RowData['labels'],
    role: data.role || '',
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.ResourcePool.SpiderAddNodes>(TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            cluster: {
              master_domain: details.clusters[item.cluster_id]?.immute_domain || '',
            },
            count: String(item.resource_spec.spider_ip_list.count),
            labels: (item.resource_spec.spider_ip_list.labels || []).map((item) => ({ id: Number(item) })),
            role: item.add_spider_role,
            specId: item.resource_spec.spider_ip_list.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      add_spider_role: string;
      cluster_id: number;
      resource_spec: {
        spider_ip_list: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          add_spider_role: item.role,
          cluster_id: item.cluster.id,
          resource_spec: {
            spider_ip_list: {
              count: Number(item.count),
              label_names: item.labels.map((item) => item.value),
              labels: item.labels.map((item) => String(item.id)),
              spec_id: item.specId,
            },
          },
        })),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
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
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          cluster: {
            master_domain: item.master_domain,
          },
          count: item.count,
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          role: (item.role as string).toLocaleLowerCase(),
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };
</script>
