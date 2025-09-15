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
    <div class="mongo-add-shard-page db-toolbox">
      <BkAlert
        class="mb-16"
        closable
        theme="info"
        :title="t('为分片集群增加分片，新增的分片数只能是“单机分片数”的倍数')" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          :key="tableKey"
          ref="editableTableRef"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
              field="cluster.master_domain"
              :label="t('目标集群')"
              :selected="selected"
              :set-current-spec-id-method="getCurrentSpecId"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('当前集群分片数')"
              readonly
              :width="120">
              <EditableBlock :placeholder="t('自动生成')">
                {{ item.cluster.id ? item.cluster.shard_num : '' }}
              </EditableBlock>
            </EditableColumn>
            <AddShardsNumColumn
              v-model="item.add_shards_num"
              :single-host-shard-num="item.cluster.single_host_shard_num"
              @batch-edit="handleBatchEdit" />
            <EditableColumn
              :label="t('最终集群分片数')"
              readonly
              :width="120">
              <EditableBlock :placeholder="t('自动生成')">
                {{ item.cluster.id ? item.cluster.shard_num + item.add_shards_num : '' }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('单机分片数')"
              readonly
              :width="120">
              <EditableBlock :placeholder="t('自动生成')">
                {{ item.cluster.id ? item.cluster.single_host_shard_num : '' }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('每片节点数')"
              readonly
              :width="120">
              <EditableBlock :placeholder="t('自动生成')">
                {{ item.cluster.id ? item.cluster.shard_node_count : '' }}
              </EditableBlock>
            </EditableColumn>
            <SpecColumn
              v-model="item.cluster.current_spec_id"
              :cluster-type="DBTypes.MONGODB"
              field="cluster.current_spec_id"
              label="当前规格"
              :machine-type="MachineTypes.MONGODB"
              required />
            <EditableColumn
              :label="t('新增机器（组）')"
              readonly
              :width="120">
              <EditableBlock :placeholder="t('自动生成')">
                {{ item.cluster.id ? getAddMachinePair(item.add_shards_num, item.cluster.single_host_shard_num) : '' }}
              </EditableBlock>
            </EditableColumn>
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

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import AddShardsNumColumn from './components/AddShardsNumColumn.vue';

  export interface IDataRow {
    add_shards_num: number;
    cluster: {
      cluster_type: string;
      current_spec_id: number;
      disaster_tolerance_level: string;
      id: number;
      machine_instance_num: number;
      major_version: string;
      master_domain: string;
      mongodb: MongodbModel['mongodb'];
      mongodb_machine_num: number;
      mongodb_machine_pair: number;
      region: string;
      shard_node_count: number;
      shard_num: number;
      single_host_shard_num: number;
    };
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    add_shards_num: values.add_shards_num || 1,
    cluster: Object.assign(
      {
        cluster_type: '',
        current_spec_id: 0,
        disaster_tolerance_level: '',
        id: 0,
        machine_instance_num: 0,
        major_version: '',
        master_domain: '',
        mongodb: [] as MongodbModel['mongodb'],
        mongodb_machine_num: 0,
        mongodb_machine_pair: 0,
        region: '',
        shard_node_count: 0,
        shard_num: 0,
        single_host_shard_num: 0,
      },
      values.cluster,
    ),
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.AddShard>(TicketTypes.MONGODB_ADD_SHARD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;

      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) => {
          const clusterItem = clusters[infoItem.cluster_id];
          return createRowData({
            add_shards_num: infoItem.add_shards_num,
            cluster: {
              master_domain: clusterItem?.immute_domain || '',
            } as IDataRow['cluster'],
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      add_shards_num: number; // 新增分片数
      city_code: string;
      cluster_id: number;
      current_shard_nodes_num: number; // 当前每分片节点数
      current_shards_num: number; // 展示用
      db_version: string;
      disaster_tolerance_level: string; // 亲和性
      node_replicaset_count: number; // 单机部署实例数
      resource_spec: {
        shard_nodes: {
          count: number; // 台数
          spec_id: number;
        };
      };
      single_host_shard_num: number; // 展示用
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MONGODB_ADD_SHARD);

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
    {
      case: '1',
      key: 'add_shards_num',
      label: t('新增集群分片数'),
    },
  ];

  const editableTableRef = useTemplateRef('editableTableRef');

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const getCurrentSpecId = (data: MongodbModel) => data.mongodb[0]!.spec_config.id;

  // 获取新增机器组数： 新增的分片数 / 单机分片数
  const getAddMachinePair = (addShardNum: number, singleHostShardNum: number) => {
    return addShardNum / singleHostShardNum;
  };

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              current_spec_id: getCurrentSpecId(item),
              disaster_tolerance_level: item.disaster_tolerance_level,
              id: item.id,
              machine_instance_num: item.machine_instance_num,
              major_version: item.major_version,
              master_domain: item.master_domain,
              mongodb: item.mongodb,
              mongodb_machine_num: item.mongodb_machine_num,
              mongodb_machine_pair: item.mongodb_machine_pair,
              region: item.region,
              shard_node_count: item.shard_node_count,
              shard_num: item.shard_num,
              single_host_shard_num: item.single_host_shard_num,
            },
          }),
        );
      }
    });
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        add_shards_num: item.add_shards_num ? Number(item.add_shards_num) : 0,
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }

    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleBatchEdit = (value: number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => ({
            add_shards_num: tableRow.add_shards_num,
            city_code: tableRow.cluster.region,
            cluster_id: tableRow.cluster.id,
            current_shard_nodes_num: tableRow.cluster.shard_node_count,
            current_shards_num: tableRow.cluster.shard_num,
            db_version: tableRow.cluster.major_version,
            disaster_tolerance_level: tableRow.cluster.disaster_tolerance_level,
            node_replicaset_count: tableRow.cluster.machine_instance_num,
            resource_spec: {
              shard_nodes: {
                count:
                  getAddMachinePair(tableRow.add_shards_num, tableRow.cluster.single_host_shard_num) *
                  tableRow.cluster.shard_node_count, // 机器组数 * 每片节点数
                spec_id: tableRow.cluster.current_spec_id,
              },
            },
            single_host_shard_num: tableRow.cluster.single_host_shard_num,
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
  .mongo-add-shard-page {
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
