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
  <UpgradeWrapper
    v-model="formData"
    @change="handleReset">
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="formData.tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterWithRelatedClustersColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleClusterBatchEdit" />
          <EditableColumn
            field="cluster_type"
            :label="t('集群类型')"
            :min-width="120"
            readonly>
            <EditableBlock
              v-if="!item.cluster.id"
              :placeholder="t('自动生成')" />
            <EditableBlock v-else>
              <BkTag
                v-if="item.cluster.cluster_type === ClusterTypes.MONGO_REPLICA_SET"
                theme="info">
                {{ t('副本集') }}
              </BkTag>
              <BkTag
                v-else-if="item.cluster.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER"
                theme="success">
                {{ t('分片集群') }}
              </BkTag>
              <span v-else>--</span>
            </EditableBlock>
          </EditableColumn>
          <EditableColumn
            field="current_version"
            :label="t('当前版本')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.cluster.major_version"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <DestVersionColumn
            v-model="item.dest_version"
            :batch-version-list="batchVersionList"
            :cluster="item.cluster"
            @batch-edit="handleBatchEdit"
            @request-success="handleVersionLoaded" />
          <OperationColumn
            :create-row-method="createTableRow"
            :table-data="formData.tableData" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
      <template #action>
        <BkButton
          class="mr-8 w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbResetButton
          class="ml-8"
          :confirm-handler="handleReset"
          :disabled="isSubmitting" />
      </template>
    </SmartAction>
  </UpgradeWrapper>
</template>

<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterWithRelatedClustersColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-with-related-clusters-column/Index.vue';

  import { random } from '@utils';

  import DestVersionColumn, { type VersionData, type VersionGroup } from './components/DestVersionColumn.vue';
  import UpgradeWrapper from './components/UpgradeWrapper.vue';

  /** 升级策略类型 */
  type UpgradeStrategy = 'rolling' | 'full_stop';

  interface RowData {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_type: ClusterTypes;
      id: number;
      major_version: string;
      master_domain: string;
      related_clusters: {
        domain: string;
        id: number;
      }[];
    };
    dest_version: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
    {
      case: '6.0.18',
      key: 'dest_version',
      label: t('目标版本'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        cluster_type: '',
        id: 0,
        major_version: '',
        master_domain: '',
        related_clusters: [] as RowData['cluster']['related_clusters'],
      },
      data?.cluster,
    ),
    dest_version: data.dest_version || '',
  });

  const formData = reactive({
    payload: createTicketPayload(),
    strategy: 'rolling' as UpgradeStrategy,
    tableData: [createTableRow()],
    tableKey: random(),
  });

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  // 各集群版本列表（由子组件上报）
  const clusterVersionMap = ref<Record<number, VersionData>>({});

  // 批量编辑：所有已选集群的可升级版本交集，按主版本分组
  const batchVersionList = computed<VersionGroup[]>(() => {
    const allData = Object.values(clusterVersionMap.value);
    if (allData.length === 0) return [];
    // 按 major 分组合并，取各集群同一 major 下 full_list 的交集
    const majorMap = new Map<string, string[][]>();
    allData.flat().forEach(({ full_list, major }) => {
      if (!majorMap.has(major)) majorMap.set(major, []);
      majorMap.get(major)!.push(full_list);
    });
    return Array.from(majorMap.entries())
      .filter(([, lists]) => lists.length === allData.length) // 只保留所有集群都有的 major
      .map(([major, lists]) => ({
        children: lists.reduce((a, b) => a.filter((v) => b.includes(v))).map((v) => ({ label: v, value: v })),
        label: major,
      }))
      .filter((group) => group.children.length > 0);
  });

  const handleVersionLoaded = (clusterId: number, data: VersionData) => {
    clusterVersionMap.value = { ...clusterVersionMap.value, [clusterId]: data };
  };

  // 清理已移除集群的版本数据
  watch(
    () => selected.value.map((item) => item.id),
    (ids) => {
      const idSet = new Set(ids);
      clusterVersionMap.value = Object.fromEntries(
        Object.entries(clusterVersionMap.value).filter(([id]) => idSet.has(Number(id))),
      );
    },
  );

  useTicketDetail<Mongodb.UpgradeVersion>(TicketTypes.MONGODB_UPGRADE_VERSION, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      formData.strategy = details.infos?.[0]?.strategy || 'rolling';
      nextTick(() => {
        Object.assign(formData, {
          payload: createTicketPayload(ticketDetail),
          tableData: infos.map((item) =>
            createTableRow({
              cluster: {
                master_domain: clusters[item.cluster_id_list[0]].immute_domain,
              } as RowData['cluster'],
              dest_version: item.dest_version,
            }),
          ),
          tableKey: random(),
        });
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    bk_cloud_id: number;
    infos: {
      bk_cloud_id: number;
      cluster_id_list: number[];
      current_version: string;
      dest_version: string;
      strategy: UpgradeStrategy;
    }[];
  }>(TicketTypes.MONGODB_UPGRADE_VERSION);

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: RowData[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...newList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        cluster: {
          master_domain: item.domain,
        } as RowData['cluster'],
        dest_version: item.dest_version || '',
      }),
    );
    if (isClear) {
      formData.tableKey = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        bk_cloud_id: formData.tableData[0]?.cluster.bk_cloud_id ?? 0,
        infos: formData.tableData.map((tableRow) => ({
          bk_cloud_id: tableRow.cluster.bk_cloud_id ?? 0,
          cluster_id_list: [tableRow.cluster.id, ...tableRow.cluster.related_clusters.map((item) => item.id)],
          current_version: tableRow.cluster.major_version!,
          dest_version: tableRow.dest_version,
          strategy: formData.strategy,
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, {
      payload: createTicketPayload(),
      tableData: [createTableRow()],
      tableKey: random(),
    });
  };
</script>

<style lang="less" scoped>
  :deep(.is-error .related-clusters) {
    background: initial;
  }
</style>
