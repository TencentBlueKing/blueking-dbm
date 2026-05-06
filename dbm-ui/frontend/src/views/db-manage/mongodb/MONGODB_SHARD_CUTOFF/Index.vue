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
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
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
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :cluster-type="formData.clusterType"
            :selected="selected"
            @batch-edit="handleHostBatchEdit" />
          <EditableColumn
            :label="t('角色类型')"
            readonly
            :width="200">
            <EditableBlock v-if="item.host.machine_type">
              {{ getRoleType(item) }}
            </EditableBlock>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('所属集群')"
            :min-width="350"
            readonly
            :rowspan="item.rowspan">
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
                  :key="cluster?.id">
                  -- {{ cluster?.master_domain }}
                </p>
              </div>
            </div>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <SpecColumn
            v-model="item.host.spec_config.id"
            :cluster-type="DBTypes.MONGODB"
            field="host.spec_config.id"
            :label="t('规格')"
            :machine-type="item.host.machine_type"
            required
            :rowspan="item.rowspan"
            @batch-edit="handleBatchEdit" />
          <ResourceTagColumn
            v-model="item.labels"
            :rowspan="item.rowspan"
            @batch-edit="handleBatchEdit" />
          <AvailableResourceColumn
            :params="{
              city: item.host.related_clusters?.[0]?.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.MONGODB, 'PUBLIC'],
              spec_id: item.host.spec_config.id,
              labels: item.labels.map((item) => item.id).join(','),
            }"
            :rowspan="item.rowspan" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createRowData" />
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
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
  import HostColumn from '@views/db-manage/mongodb/common/toolbox-field/cutoff/HostColumn.vue';

  import { random } from '@utils';

  interface IDataRow {
    host: {
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      cluster_type: MongodbInstanceModel['cluster_type'];
      ip: string;
      machine_type: MachineTypes;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
        region: string;
      }[];
      shard: string;
      spec_config: MongodbInstanceModel['spec_config'];
    };
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    rowspan: number;
  }

  const { t } = useI18n();
  const router = useRouter();

  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('待替换的主机'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createRowData = (values: DeepPartial<IDataRow> = {}) => ({
    host: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_id: 0,
        cluster_type: '' as MongodbInstanceModel['cluster_type'],
        ip: '',
        machine_type: '' as MachineTypes,
        master_domain: '',
        related_clusters: [] as IDataRow['host']['related_clusters'],
        shard: '',
        spec_config: {} as MongodbInstanceModel['spec_config'],
      },
      values.host,
    ),
    labels: (values.labels || []) as IDataRow['labels'],
    rowspan: values.rowspan || 1,
  });

  const getClusterNodeCount = (clusterId: number) => {
    const countMap: Record<string, number> = {};
    formData.tableData.forEach((tableItem) => {
      if (tableItem.host.ip && tableItem.host.cluster_id) {
        if (tableItem.host.cluster_id !== clusterId) {
          return;
        }
        const { machine_type: machineType, shard } = tableItem.host;
        const nodeKey =
          tableItem.host.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && tableItem.host.machine_type === 'mongodb'
            ? shard
            : machineType;
        if (countMap[nodeKey]) {
          countMap[nodeKey] = countMap[nodeKey] + 1;
        } else {
          countMap[nodeKey] = 1;
        }
      }
    }, {});

    const typeCountMap: Record<string, number[]> = {
      mongo_config: [],
      mongodb: [],
      mongos: [],
    };
    Object.entries(countMap).forEach(([type, count]) => {
      if (type in typeCountMap) {
        typeCountMap[type].push(count);
      } else {
        typeCountMap.mongodb.push(count);
      }
    });
    return typeCountMap;
  };

  const rules = {
    'host.ip': [
      {
        message: '',
        trigger: 'change',
        validator: (value: string, { rowData }: { rowData: IDataRow }) => {
          const nodeCountMap = getClusterNodeCount(rowData.host.cluster_id);

          if (nodeCountMap.mongo_config.some((mongoConfigItem) => mongoConfigItem > 1)) {
            return t('config一次只能替换一个节点');
          }
          if (nodeCountMap.mongodb.some((mongoConfigItem) => mongoConfigItem > 1)) {
            return t('同一个shard，同时只能替换一个节点');
          }

          if (Object.values(nodeCountMap).filter((item) => item.length > 0).length !== 1) {
            return t('一个集群只能替换一个角色');
          }

          return true;
        },
      },
    ],
  };

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());

  const formData = reactive({
    clusterType: ClusterTypes.MONGO_SHARED_CLUSTER,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const selected = computed(() => formData.tableData.filter((item) => item.host.ip).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mongodb.ResourcePool.ShardCutoff>(TicketTypes.MONGODB_SHARD_CUTOFF, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
        clusterType: clusters[infos[0].cluster_id].cluster_type,
        tableData: infos.flatMap((infoItem) => {
          const machineInfoList = [
            ...(infoItem.mongo_config || []),
            ...(infoItem.mongodb || []),
            ...(infoItem.mongos || []),
          ];
          return machineInfoList.map((machineInfo) =>
            createRowData({
              host: {
                ip: machineInfo.ip,
                master_domain: clusters[infoItem.cluster_id].immute_domain,
              } as IDataRow['host'],
              labels: (Object.values(infoItem.resource_spec)[0].labels || []).map((item) => ({ id: Number(item) })),
            }),
          );
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER;
    infos: Mongodb.ResourcePool.ShardCutoff['infos'];
    ip_source: 'resource_pool';
  }>(TicketTypes.MONGODB_SHARD_CUTOFF);

  watch(
    () => formData.tableData.length,
    () => {
      sortTableByCluster();
    },
  );

  const handleClusterTypeChange = () => {
    router.push({
      name: TicketTypes.MONGODB_REPLICASET_CUTOFF,
    });
  };

  const generateRequestParam = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    formData.tableData.forEach((item) => {
      if (item.host.ip) {
        const domain = item.host.master_domain;
        if (!clusterMap[domain]) {
          clusterMap[domain] = [item];
        } else {
          clusterMap[domain].push(item);
        }
      }
    });
    const domains = Object.keys(clusterMap);
    const infos = domains.map((domain) => {
      const sameArr = clusterMap[domain];
      const infoItem = {
        cluster_id: sameArr[0].host.cluster_id,
        mongo_config: [] as NonNullable<Mongodb.ResourcePool.ShardCutoff['infos'][number]['mongo_config']>,
        mongodb: [] as NonNullable<Mongodb.ResourcePool.ShardCutoff['infos'][number]['mongodb']>,
        mongos: [] as NonNullable<Mongodb.ResourcePool.ShardCutoff['infos'][number]['mongos']>,
        old_nodes: {} as Mongodb.ResourcePool.ShardCutoff['infos'][number]['old_nodes'],
        resource_spec: {} as NonNullable<Mongodb.ResourcePool.ShardCutoff['infos'][number]['resource_spec']>,
        switch_role: '',
      };
      sameArr.forEach((item) => {
        const specObj = {
          bk_cloud_id: item.host.bk_cloud_id,
          bk_host_id: item.host.bk_host_id,
          down: false,
          ip: item.host.ip,
          spec: item.host.spec_config,
        };
        infoItem[
          item.host.machine_type as keyof Omit<
            typeof infoItem,
            'cluster_id' | 'resource_spec' | 'switch_role' | 'old_nodes'
          >
        ].push(specObj);
      });

      const getResourceSpecInfo = (count: number, specInfo: IDataRow) => ({
        count,
        label_names: specInfo.labels.map((item) => item.value),
        labels: specInfo.labels.map((item) => String(item.id)),
        spec_id: specInfo.host.spec_config.id,
      });

      if (infoItem.mongo_config.length > 0) {
        Object.assign(infoItem.resource_spec, {
          new_mongo_config: getResourceSpecInfo(infoItem.mongo_config.length, sameArr[0]),
        });
        infoItem.switch_role = 'mongo_config';
        infoItem.old_nodes.mongo_config = infoItem.mongo_config.map((item) => ({
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
        }));
      }
      if (infoItem.mongodb.length > 0) {
        Object.assign(infoItem.resource_spec, {
          new_mongodb: getResourceSpecInfo(infoItem.mongodb.length, sameArr[0]),
        });
        infoItem.switch_role = 'mongodb';
        infoItem.old_nodes.mongodb = infoItem.mongodb.map((item) => ({
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
        }));
      }
      if (infoItem.mongos.length > 0) {
        Object.assign(infoItem.resource_spec, {
          new_mongos: getResourceSpecInfo(infoItem.mongos.length, sameArr[0]),
        });
        infoItem.switch_role = 'mongos';
        infoItem.old_nodes.mongos = infoItem.mongos.map((item) => ({
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
        }));
      }

      return infoItem;
    });
    return infos;
  };

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
        infos: generateRequestParam(),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, {
      payload: createTickePayload(),
      tableData: [createRowData()],
    });
  };

  const handleHostBatchEdit = (list: MongodbInstanceModel[]) => {
    const newList = list.reduce<IDataRow[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createRowData({
            host: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              cluster_type: item.cluster_type,
              ip: item.ip,
              machine_type: item.machine_type as MachineTypes,
              master_domain: item.master_domain,
              related_clusters: item.related_clusters
                // .map((cluster) => ({
                //   id: cluster.id,
                //   master_domain: cluster.master_domain,
                //   region: cluster.region,
                // }))
                .filter((cluster) => cluster.master_domain !== item.master_domain),
              shard: item.shard,
              spec_config: item.spec_config as MongodbInstanceModel['spec_config'],
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
  };

  const handleBatchEdit = (value: string | string[] | number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        host: {
          ip: item.ip,
        } as IDataRow['host'],
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

  const getRoleType = (item: IDataRow) => {
    if (item.host.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && item.host.machine_type === 'mongodb') {
      return item.host.shard;
    }
    return item.host.machine_type || '';
  };

  const sortTableByCluster = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    const emptyRowList: IDataRow[] = [];
    formData.tableData.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const { master_domain: domain } = item.host;
      if (!domain) {
        emptyRowList.push(item);
        return;
      }
      if (!clusterMap[domain]) {
        clusterMap[domain] = [item];
      } else {
        clusterMap[domain].push(item);
      }
    });

    const sortedList: IDataRow[] = [];
    Object.values(clusterMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
      sortedList.push(...list);
    });

    return [...sortedList, ...emptyRowList];
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
