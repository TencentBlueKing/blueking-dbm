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
    <div class="proxy-scale-down-page db-toolbox">
      <BkAlert
        closable
        theme="info"
        :title="t('扩容Shard节点数：xxx')" />
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
            <ClusterWithRelatedClustersColumn
              v-model="item.cluster"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('集群类型')"
              :width="200">
              <EditableBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')" />
            </EditableColumn>
            <EditableColumn
              :label="t('当前 Shard 的节点数')"
              :width="200">
              <EditableBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')">
                {{ item.cluster.shard_node_count }}
              </EditableBlock>
            </EditableColumn>
            <TargetNumColumn
              v-model="item.target_num"
              :disabled="!item.cluster.id"
              :min="item.cluster.shard_node_count"
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <BkFormItem
          v-bk-tooltips="t('如忽略_有连接的情况下也会执行')"
          class="fit-content">
          <BkCheckbox
            v-model="formData.is_ignore_business_access"
            :false-label="false"
            true-label>
            <span class="safe-action-text">{{ t('忽略业务连接') }}</span>
          </BkCheckbox>
        </BkFormItem>
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

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterWithRelatedClustersColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-with-related-clusters-column/Index.vue';

  import TargetNumColumn from './components/TargetNumColumn.vue';

  export interface IDataRow {
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      machine_instance_num: number;
      master_domain: string;
      mongodb: MongodbModel['mongos'];
      related_clusters: {
        domain: string;
        id: number;
      }[];
      shard_node_count: number;
      shard_num: number;
    };
    target_num: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        machine_instance_num: 0,
        master_domain: '',
        mongodb: [] as MongodbModel['mongos'],
        related_clusters: [] as IDataRow['cluster']['related_clusters'],
        shard_node_count: 0,
        shard_num: 0,
      },
      values.cluster,
    ),
    target_num: values.target_num || '',
  });

  const createDefaultFormData = () => ({
    is_ignore_business_access: false,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.AddShardNodes>(TicketTypes.MONGODB_ADD_SHARD_NODES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos, is_safe: isSafe } = details;

      Object.assign(formData, {
        is_ignore_business_access: !isSafe,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterItem = clusters[item.cluster_ids[0]];
          return createRowData({
            cluster: {
              master_domain: clusterItem.immute_domain,
            } as IDataRow['cluster'],
            target_num: `${item.current_shard_nodes_num + item.add_shard_nodes_num}`,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      add_shard_nodes_num: number; // 增加shard节点数
      cluster_ids: number[];
      current_shard_nodes_num: number; // 当前shard节点数
      node_replica_count: number; // 单机部署实例
      resource_spec: {
        shard_nodes: {
          count: number; // 分片数 / 每台机器的实例数 * 增加的节点数
          spec_id: number;
        };
      };
      shards_num: number; // 分片数
    }[];
    is_safe: boolean;
  }>(TicketTypes.MONGODB_ADD_SHARD_NODES);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => {
            const cluster = tableRow.cluster as Required<IDataRow['cluster']>;
            const targerNum = tableRow.target_num!;
            return {
              add_shard_nodes_num: Number(targerNum) - cluster.shard_node_count, // 增加shard节点数
              cluster_ids:
                cluster.cluster_type === ClusterTypes.MONGO_REPLICA_SET
                  ? [cluster.id, ...cluster.related_clusters.map((relatedItem) => relatedItem.id)]
                  : [cluster.id],
              current_shard_nodes_num: cluster.shard_node_count, // 当前shard节点数
              node_replica_count: cluster.machine_instance_num, // 单机部署实例
              resource_spec: {
                shard_nodes: {
                  count:
                    (cluster.shard_num / cluster.machine_instance_num) * (Number(targerNum) - cluster.shard_node_count), // 分片数 / 每台机器的实例数 * 增加的节点数
                  spec_id: cluster.mongodb[0].spec_config.id,
                },
              },
              shards_num: cluster.shard_num, // 分片数
            };
          }),
          is_safe: !formData.is_ignore_business_access,
        },
        ...formData.payload,
      });
    }
  };

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              machine_instance_num: item.machine_instance_num,
              master_domain: item.master_domain,
              mongodb: item.mongodb,
              related_clusters: [],
              shard_node_count: item.shard_node_count,
              shard_num: item.shard_num,
            },
          }),
        );
      }
    });
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: string | string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
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
