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
      :title="t('部署只读接入层：在原集群上增加Spider Slave节点，一个集群最多只能有一个')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
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
          <SpecColumn
            v-model="item.specId"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :current-spec-id="item.cluster.spec_id"
            selectable />
          <EditableColumn
            field="count"
            :label="t('部署台数')"
            :min-width="150"
            required>
            <EditableInput
              v-model="item.count"
              :max="1024"
              :min="1"
              type="number" />
          </EditableColumn>
          <ResourceTagColumn
            v-model="item.labels"
            v-model:selected="item.labelSelected" />
          <AvailableResourceColumn
            :params="{
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.cluster.spec_id,
              labels: item.labels.join(','),
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
  import type { _DeepPartial } from 'pinia';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    count: string;
    labels: number[];
    labelSelected: ComponentProps<typeof ResourceTagColumn>['selected'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: _DeepPartial<RowData> = {}) => ({
    cluster: {
      bk_cloud_id: 0,
      id: 0,
      master_domain: '',
      spec_id: 0,
      ...data.cluster,
    },
    count: data.count || '',
    labels: (data.labels as number[]) || ([] as number[]),
    labelSelected: [] as ComponentProps<typeof ResourceTagColumn>['selected'],
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.ResourcePool.SpiderSlaveApply>(TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            cluster: {
              master_domain: details.clusters[item.cluster_id]?.immute_domain || '',
            },
            count: String(item.resource_spec.spider_slave_ip_list.count),
            labels: (item.resource_spec.spider_slave_ip_list.labels || []).map((item) => Number(item)),
            specId: item.resource_spec.spider_slave_ip_list.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      resource_spec: {
        spider_slave_ip_list: {
          count: number;
          label_values: string[]; // 标签value列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          resource_spec: {
            spider_slave_ip_list: {
              count: Number(item.count),
              label_values: item.labelSelected.map((item) => item.value),
              labels: item.labels.map((item) => String(item)),
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
</script>
