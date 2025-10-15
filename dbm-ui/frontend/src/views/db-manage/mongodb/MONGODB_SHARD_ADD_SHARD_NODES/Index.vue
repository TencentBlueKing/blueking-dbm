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
        class="mb-16"
        closable
        theme="info"
        :title="t('扩容 Shard 节点数：提供增加副本集对应的member功能，目标节点数建议为3,5,7..奇数')" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <BkFormItem
          :label="t('集群类型')"
          required>
          <BkRadioGroup
            v-model="formData.clusterType"
            style="width: 400px"
            type="card"
            @change="handleClusterTypeChange">
            <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
              {{ t('副本集集群') }}
            </BkRadioButton>
            <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
              {{ t('分片集群') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <BatchInput
          :config="batchInputConfig"
          @change="handleBatchInput" />
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
              :selected="selected"
              :set-current-spec-id-method="getCurrentSpecId"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('集群类型')"
              readonly
              :width="150">
              <EditableBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')" />
            </EditableColumn>
            <EditableColumn
              :label="t('当前节点数')"
              readonly
              :width="150">
              <EditableBlock :placeholder="t('输入集群后自动生成')">
                {{ item.cluster.id ? item.cluster.shard_node_count : '' }}
              </EditableBlock>
            </EditableColumn>
            <AddShardNodesNumColumn
              v-model="item.add_shard_nodes_num"
              :cluster-id="item.cluster.id"
              @batch-edit="handleBatchEdit" />
            <EditableColumn
              :label="t('最终节点数')"
              readonly
              :width="150">
              <EditableBlock>
                {{ item.cluster.id ? item.cluster.shard_node_count + item.add_shard_nodes_num : '' }}
              </EditableBlock>
            </EditableColumn>
            <SpecColumn
              v-model="item.cluster.current_spec_id"
              :cluster-type="DBTypes.MONGODB"
              field="cluster.current_spec_id"
              label="当前规格"
              :machine-type="MachineTypes.MONGODB"
              required />
            <ResourceTagColumn
              v-model="item.labels"
              @batch-edit="handleBatchEdit" />
            <AvailableResourceColumn
              :params="{
                city: item.cluster.region,
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MONGODB, 'PUBLIC'],
                spec_id: item.cluster.mongodb?.[0]?.spec_config.id,
                labels: item.labels.map((item) => item.id).join(','),
              }" />
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import AddShardNodesNumColumn from '@views/db-manage/mongodb/common/toolbox-field/addShardNodes/AddShardNodesNumColumn.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    add_shard_nodes_num: number;
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      current_spec_id: number;
      id: number;
      machine_instance_num: number;
      major_version: string;
      master_domain: string;
      mongodb: MongodbModel['mongos'];
      region: string;
      related_clusters: {
        domain: string;
        id: number;
      }[];
      shard_node_count: number;
      shard_num: number;
    };
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
  }

  const createRowData = (values: DeepPartial<IDataRow> = {}) => ({
    add_shard_nodes_num: values.add_shard_nodes_num || 1,
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        current_spec_id: 0,
        id: 0,
        machine_instance_num: 0,
        major_version: '',
        master_domain: '',
        mongodb: [] as MongodbModel['mongos'],
        region: '',
        related_clusters: [] as IDataRow['cluster']['related_clusters'],
        shard_node_count: 0,
        shard_num: 0,
      },
      values.cluster,
    ),
    labels: (values.labels || []) as IDataRow['labels'],
  });

  const createDefaultFormData = () => ({
    clusterType: ClusterTypes.MONGO_SHARED_CLUSTER,
    is_ignore_business_access: false,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();
  const router = useRouter();

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
    {
      case: '1',
      key: 'count',
      label: t('扩容节点数'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  useTicketDetail<Mongodb.ShardAddShardNodes>(TicketTypes.MONGODB_SHARD_ADD_SHARD_NODES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos, is_safe: isSafe } = details;

      Object.assign(formData, {
        is_ignore_business_access: !isSafe,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterItem = clusters[item.cluster_id];
          return createRowData({
            add_shard_nodes_num: item.add_shard_nodes_num,
            cluster: {
              master_domain: clusterItem.immute_domain,
            } as IDataRow['cluster'],
            labels: (item.resource_spec.shard_nodes.labels || []).map((item) => ({ id: Number(item) })),
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      add_shard_nodes_num: number; // 增加shard节点数
      cluster_id: number;
      current_shard_nodes_num: number; // 当前shard节点数
      db_version: string;
      node_replica_count: number; // 单机部署实例
      resource_spec: {
        shard_nodes: {
          count: number; // 分片数 / 每台机器的实例数 * 增加的节点数
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
      shards_num: number; // 分片数
    }[];
    is_safe: boolean;
  }>(TicketTypes.MONGODB_SHARD_ADD_SHARD_NODES);

  const editableTableRef = useTemplateRef('editableTable');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterTypeChange = () => {
    router.push({
      name: TicketTypes.MONGODB_REPLICA_ADD_SHARD_NODES,
    });
  };

  const getCurrentSpecId = (data: MongodbModel) => data.mongodb[0]!.spec_config.id;

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => {
            const cluster = tableRow.cluster as Required<IDataRow['cluster']>;
            return {
              add_shard_nodes_num: tableRow.add_shard_nodes_num, // 增加shard节点数
              cluster_id: cluster.id,
              current_shard_nodes_num: cluster.shard_node_count, // 当前shard节点数
              db_version: cluster.major_version,
              node_replica_count: cluster.machine_instance_num, // 单机部署实例
              resource_spec: {
                shard_nodes: {
                  count: (cluster.shard_num / cluster.machine_instance_num) * tableRow.add_shard_nodes_num, // 分片数 / 每台机器的实例数 * 增加的节点数
                  label_names: tableRow.labels.map((item) => item.value),
                  labels: tableRow.labels.map((item) => String(item.id)),
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
              current_spec_id: getCurrentSpecId(item),
              id: item.id,
              machine_instance_num: item.machine_instance_num,
              major_version: item.major_version,
              master_domain: item.master_domain,
              mongodb: item.mongodb,
              region: item.region,
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

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        add_shard_nodes_num: item.count ? Number(item.count) : 1,
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
        labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
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
