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
      :title="t('整机替换：将原主机上的所有实例搬迁到同等规格的新主机')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('集群类型')"
        required>
        <BkRadioGroup
          v-model="formData.clusterType"
          style="width: 400px"
          type="card"
          @change="handleReset">
          <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
            {{ t('副本集集群') }}
          </BkRadioButton>
          <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
            {{ t('分片集群') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :cluster-type="formData.clusterType"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('角色类型')"
            :min-width="200">
            <EditableBlock v-if="item.host.machine_type">
              {{ getRoleType(item) }}
            </EditableBlock>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('所属集群')"
            :min-width="200">
            <div
              v-if="item.host.master_domain"
              class="cluster-domain">
              <p>{{ item.host.master_domain }}</p>
              <div
                v-if="item.host.related_clusters.length > 0"
                class="related-clusters">
                {{ t('含n个同机关联集群', { n: item.host.related_clusters.length }) }}
                <p
                  v-for="cluster in item.host.related_clusters"
                  :key="cluster.id">
                  -- {{ cluster.master_domain }}
                </p>
              </div>
            </div>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <SpecColumn
            v-model="item.spec_id"
            :row-data="item" />
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
  import { useI18n } from 'vue-i18n';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import HostColumn from './components/HostColumn.vue';
  import SpecColumn from './components/spec-column/Index.vue';

  interface RowData {
    host: {
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      cluster_type: MongodbInstanceModel['cluster_type'];
      ip: string;
      machine_type: MongodbInstanceModel['machine_type'];
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
      shard: string;
      spec_config: MongodbInstanceModel['spec_config'];
    };
    spec_id: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    host: data.host || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      cluster_type: ClusterTypes.MONGO_REPLICA_SET as MongodbInstanceModel['cluster_type'],
      ip: '',
      machine_type: '' as MongodbInstanceModel['machine_type'],
      master_domain: '',
      related_clusters: [],
      shard: '',
      spec_config: {} as MongodbInstanceModel['spec_config'],
    },
    spec_id: data.spec_id || 0,
  });

  const formData = reactive({
    clusterType: ClusterTypes.MONGO_REPLICA_SET,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const selected = computed(() => formData.tableData.filter((item) => item.host.ip).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mongodb.Cutoff>(TicketTypes.MONGODB_CUTOFF, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos, specs } = details;
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
      });
      if (infos.length > 0) {
        const dataList: RowData[] = [];
        infos.forEach((info) => {
          const hostList = [...info.mongo_config, ...info.mongodb, ...info.mongos];
          let machineType = '';
          if (info.mongo_config.length) {
            machineType = 'mongo_config';
          }
          if (info.mongodb.length) {
            machineType = 'mongodb';
          }
          if (info.mongos.length) {
            machineType = 'mongos';
          }
          const clusterInfo = clusters[info.cluster_id];
          hostList.forEach((item) => {
            const specInfo = specs[info.resource_spec[`${machineType}_${item.ip}`].spec_id];
            dataList.push(
              createTableRow({
                host: {
                  bk_cloud_id: item.bk_cloud_id,
                  bk_host_id: item.bk_host_id,
                  cluster_id: info.cluster_id,
                  cluster_type: clusterInfo.cluster_type,
                  ip: item.ip,
                  machine_type: machineType,
                  master_domain: clusterInfo.immute_domain,
                  related_clusters: [],
                  shard: '',
                  spec_config: specInfo as unknown as MongodbInstanceModel['spec_config'],
                },
                spec_id: specInfo.id,
              }),
            );
          });
        });
        formData.clusterType = dataList[0].host.cluster_type;
        formData.tableData = [...dataList];
      }
    },
  });

  type SpecHostList = {
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    spec_id: number;
  }[];

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      mongo_config: SpecHostList;
      mongodb: SpecHostList;
      mongos: SpecHostList;
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MONGODB_CUTOFF);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => {
          const infoItem = {
            cluster_id: item.host.cluster_id,
            mongo_config: [] as SpecHostList,
            mongodb: [] as SpecHostList,
            mongos: [] as SpecHostList,
          };
          Object.assign(infoItem, {
            [item.host.machine_type]: [
              {
                bk_cloud_id: item.host.bk_cloud_id,
                bk_host_id: item.host.bk_host_id,
                ip: item.host.ip,
                spec_id: item.spec_id,
              },
            ],
          });
          return infoItem;
        }),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, {
      payload: createTickePayload(),
      tableData: [createTableRow()],
    });
  };

  const handleBatchEdit = (list: MongodbInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              cluster_type: item.cluster_type,
              ip: item.ip,
              machine_type: item.machine_type,
              master_domain: item.master_domain,
              related_clusters: item.related_clusters
                .map((cluster) => ({
                  id: cluster.id,
                  master_domain: cluster.master_domain,
                }))
                .filter((cluster) => cluster.master_domain !== item.master_domain),
              shard: item.shard,
              spec_config: item.spec_config as MongodbInstanceModel['spec_config'],
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const getRoleType = (item: RowData) => {
    if (item.host.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && item.host.machine_type === 'mongodb') {
      return item.host.shard;
    }
    return item.host.machine_type || '';
  };
</script>
<style lang="less" scoped>
  .cluster-domain {
    width: 100%;

    > p {
      padding: 0 8px;
      line-height: 40px;
    }

    .related-clusters {
      padding: 8px;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      background: #fafbfd;
    }
  }
</style>
