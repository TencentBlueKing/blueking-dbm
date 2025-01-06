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
    <div class="proxy-scale-down-page">
      <BkAlert
        closable
        theme="info"
        :title="t('缩容Shard节点数：xxx')" />
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
            <EditClusterWithRelatedClustersColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER]"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditableTableColumn
              :label="t('集群类型')"
              :width="200">
              <EditBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')" />
            </EditableTableColumn>
            <EditableTableColumn
              :label="t('当前 Shard 的节点数')"
              :width="200">
              <EditBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')">
                {{ item.cluster.shard_node_count }}
              </EditBlock>
            </EditableTableColumn>
            <TargetNumberColumn
              v-model="item.target_num"
              :disabled="!item.cluster.id"
              :max="item.cluster.shard_node_count" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="tableData" />
          </EditableTableRow>
        </EditableTable>
        <IgnoreBiz
          v-model="formData.is_ignore_business_access"
          v-bk-tooltips="t('如忽略_有连接的情况下也会执行')" />
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

  import EditableTable, {
    Block as EditBlock,
    Column as EditableTableColumn,
    Row as EditableTableRow,
  } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';
  import EditClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-column/Index.vue';
  import EditClusterWithRelatedClustersColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-with-related-clusters-column/Index.vue';

  import TargetNumberColumn from './components/TargetNumberColumn.vue';

  export interface IDataRow {
    cluster: {
      id?: number;
      master_domain?: string;
      related_clusters?: {
        id: number;
        domain: string;
      }[];
      cluster_type?: string;
      cluster_type_name?: string;
      shard_node_count?: number;
      machine_instance_num?: number;
      shard_num?: number;
    };
    target_num?: number;
  }

  const createRowData = (values?: Partial<IDataRow>) => ({
    cluster: values?.cluster ? values.cluster : ({} as IDataRow['cluster']),
    target_num: values?.target_num,
  });

  const createDefaultFormData = () => ({
    is_ignore_business_access: false,
    remark: '',
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.ReduceShardNodes>(TicketTypes.MONGODB_REDUCE_SHARD_NODES, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters, is_safe: isSafe } = details;
      tableData.value = infos.map((item) => {
        const clusterItem = clusters[item.cluster_ids[0]];
        return createRowData({
          cluster: {
            master_domain: clusterItem.immute_domain,
          },
          target_num: item.current_shard_nodes_num - item.reduce_shard_nodes,
        });
      });
      Object.assign(formData, {
        is_ignore_business_access: !isSafe,
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      current_shard_nodes_num: number; // 当前shard节点数
      reduce_shard_nodes: number; // 当前 - 缩容至
      shard_num: number; // 分片数
      machine_instance_num: number; // 单机部署实例
    }[];
    is_safe: boolean;
  }>(TicketTypes.MONGODB_REDUCE_SHARD_NODES);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            return domainList.value.filter((domain) => domain === value).length === 1;
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

  const domainList = computed(() =>
    tableData.value.flatMap((tableRow) => {
      if (tableRow.cluster.master_domain) {
        return [
          tableRow.cluster.master_domain || '',
          ...(tableRow.cluster.related_clusters || []).map((relatedItem) => relatedItem.domain),
        ];
      }
      return [];
    }),
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
              cluster_type_name: item.cluster_type_name,
              shard_node_count: item.shard_node_count,
              machine_instance_num: item.machine_instance_num,
              shard_num: item.shard_num,
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
          is_safe: !formData.is_ignore_business_access,
          infos: tableData.value.map((tableRow) => {
            const cluster = tableRow.cluster as Required<IDataRow['cluster']>;
            const targerNum = tableRow.target_num!;
            return {
              cluster_ids:
                cluster.cluster_type === ClusterTypes.MONGO_REPLICA_SET
                  ? [cluster.id, ...cluster.related_clusters.map((relatedItem) => relatedItem.id)]
                  : [cluster.id],
              reduce_shard_nodes: cluster.shard_node_count - targerNum, // 当前 - 缩容至
              current_shard_nodes_num: cluster.shard_node_count, // 当前shard节点数
              shard_num: cluster.shard_num, // 分片数
              machine_instance_num: cluster.machine_instance_num, // 单机部署实例
            };
          }),
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
  .proxy-scale-down-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
