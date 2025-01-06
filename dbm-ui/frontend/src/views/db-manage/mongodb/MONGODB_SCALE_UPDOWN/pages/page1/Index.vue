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
          class="mt16 mb16"
          :model="tableData"
          :rules="rules">
          <EditableTableRow
            v-for="(item, index) in tableData"
            :key="index">
            <EditClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER]"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <CurrentCapacityColumn :data="item.cluster" />
            <TargetCapacityColumn
              v-model="item.target_capacity"
              :data="item.cluster" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="tableData" />
          </EditableTableRow>
        </EditableTable>
        <TicketRemark v-model="formData.remark" />
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';
  import EditClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-column/Index.vue';

  import CurrentCapacityColumn from './components/CurrentCapacityColumn.vue';
  import TargetCapacityColumn from './components/target-capacity-column/Index.vue';

  export interface IDataRow {
    cluster: {
      id?: number;
      master_domain?: string;
      cluster_type?: string;
      mongodb?: MongodbModel['mongodb'];
      shard_spec?: string;
      shard_node_count?: number;
      shard_num?: number;
      mongodb_machine_pair?: number;
      mongodb_machine_num?: number;
      bk_cloud_id?: number;
    };
    target_capacity?: {
      shard_machine_group: number;
      shard_node_count: number;
      shards_num: number;
      resource_spec: {
        mongodb: {
          spec_id: number;
          count: number;
        };
      };
    };
  }

  const createRowData = (values?: Partial<IDataRow>) => ({
    cluster: values?.cluster ? values.cluster : ({} as IDataRow['cluster']),
    target_capacity: values?.target_capacity,
  });

  const createDefaultFormData = () => ({
    remark: '',
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.ScaleUpdown>(TicketTypes.MONGODB_SCALE_UPDOWN, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;
      tableData.value = infos.map((item) => {
        const clusterItem = clusters[item.cluster_id];
        return createRowData({
          cluster: {
            master_domain: clusterItem.immute_domain,
          },
        });
      });
      Object.assign(formData, {
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
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

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = tableData.value.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
  };

  const tableData = ref<IDataRow[]>([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof EditClusterColumn>['selected'] = {
      [ClusterTypes.MONGO_REPLICA_SET]: [],
      [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    };
    tableData.value.forEach((tableRow) => {
      const { id, cluster_type: clusterType, master_domain: masterDomain } = tableRow.cluster;
      if (id && clusterType && masterDomain) {
        selectedClusters[clusterType as keyof typeof selectedClusters].push({
          id,
          master_domain: masterDomain,
        });
      }
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
              cluster_type: item.cluster_type,
              mongodb: item.mongodb,
              shard_spec: item.shard_spec,
              shard_node_count: item.shard_node_count,
              shard_num: item.shard_num,
              mongodb_machine_pair: item.mongodb_machine_pair,
              mongodb_machine_num: item.mongodb_machine_num,
              bk_cloud_id: item.bk_cloud_id,
            },
          }),
        );
      }
    });
    tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          ip_source: 'resource_pool',
          infos: tableData.value.map((tableRow) => ({
            cluster_id: tableRow.cluster.id!,
            ...tableRow.target_capacity!,
          })),
        },
        remark: formData.remark,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    tableData.value = [createRowData()];
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .master-failover-page {
    padding-bottom: 20px;
  }
</style>
