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
    <div class="master-failover-page">
      <BkAlert
        closable
        theme="info"
        :title="t('集群容量变更：通过部署新集群来实现原集群的扩容或缩容（集群分片数不变），可以指定新的版本')" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <CurrentCapacityColumn v-model="item.cluster" />
            <TargetCapacityColumn
              v-model="item.target_capacity"
              :cluster="item.cluster" />
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
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  import CurrentCapacityColumn from './components/CurrentCapacityColumn.vue';
  import TargetCapacityColumn from './components/target-capacity-column/Index.vue';

  export interface IDataRow {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_name: string;
      cluster_type: string;
      id: number;
      master_domain: string;
      mongodb: MongodbModel['mongodb'];
      mongodb_machine_num: number;
      mongodb_machine_pair: number;
      shard_node_count: number;
      shard_num: number;
      shard_spec: string;
    };
    target_capacity: {
      resource_spec: {
        mongodb: {
          count: number;
          spec_id: number;
        };
      };
      shard_machine_group: number;
      shard_node_count: number;
      shards_num: number;
    };
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        cluster_name: '',
        cluster_type: '',
        id: 0,
        master_domain: '',
        mongodb: [] as MongodbModel['mongodb'],
        mongodb_machine_num: 0,
        mongodb_machine_pair: 0,
        shard_node_count: 0,
        shard_num: 0,
        shard_spec: '',
      },
      values?.cluster,
    ),
    target_capacity: Object.assign(
      {
        resource_spec: {
          mongodb: {
            count: 0,
            spec_id: 0,
          },
        },
        shard_machine_group: 0,
        shard_node_count: 0,
        shards_num: 0,
      },
      values.target_capacity,
    ),
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();
  const route = useRoute();

  useTicketDetail<Mongodb.ScaleUpdown>(TicketTypes.MONGODB_SCALE_UPDOWN, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterItem = clusters[item.cluster_id];
          return createRowData({
            cluster: {
              master_domain: clusterItem.immute_domain,
            } as IDataRow['cluster'],
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      resource_spec: {
        mongodb: {
          count: number;
          spec_id: number;
        };
      };
      shard_machine_group: number;
      shard_node_count: number;
      shards_num: number;
    }[];
    ip_source: string;
  }>(TicketTypes.MONGODB_SCALE_UPDOWN);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  // 集群列表及详情跳转
  const { masterDomain } = route.query;
  if (masterDomain) {
    Object.assign(formData, {
      tableData: [
        createRowData({
          cluster: {
            master_domain: masterDomain,
          } as IDataRow['cluster'],
        }),
      ],
    });
  }

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_biz_id: item.bk_biz_id,
              bk_cloud_id: item.bk_cloud_id,
              cluster_name: item.cluster_name,
              cluster_type: item.cluster_type,
              id: item.id,
              master_domain: item.master_domain,
              mongodb: item.mongodb,
              mongodb_machine_num: item.mongodb_machine_num,
              mongodb_machine_pair: item.mongodb_machine_pair,
              shard_node_count: item.shard_node_count,
              shard_num: item.shard_num,
              shard_spec: item.shard_spec,
            },
          }),
        );
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => ({
            cluster_id: tableRow.cluster.id,
            ...tableRow.target_capacity,
          })),
          ip_source: 'resource_pool',
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

<style lang="less" scoped>
  .master-failover-page {
    padding-bottom: 20px;
  }
</style>
