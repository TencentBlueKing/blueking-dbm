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
    <div class="version-upgrade-page">
      <BkAlert
        closable
        theme="info"
        :title="t('版本升级：将集群的接入层或存储层，更新到指定版本')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
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
              :label="t('架构版本')"
              :width="200">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <NodeTypeColumn
              v-model="item.node_type"
              :cluster="item.cluster"
              :cluster-type="item.cluster.cluster_type"
              @batch-edit="handleNodeTypeBatchEdit" />
            <CurrentVersionColumn
              v-model="item.current_versions"
              :cluster-id="item.cluster.id"
              :node-type="item.node_type" />
            <TargetVersionColumn
              v-model="item.target_version"
              :cluster-id="item.cluster.id"
              :current-versions="item.current_versions"
              :node-type="item.node_type" />
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

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';
  import { findRelatedClustersByClusterIds } from '@services/source/redisToolbox';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterWithRelatedClustersColumn from '@views/db-manage/redis/common/toolbox-field/cluster-with-related-clusters-column/Index.vue';

  import CurrentVersionColumn from './components/CurrentVersionColumn.vue';
  import NodeTypeColumn from './components/NodeTypeColumn.vue';
  import TargetVersionColumn from './components/TargetVersionColumn.vue';

  interface IDataRow {
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      related_clusters: {
        cluster_type: string;
        id: number;
        master_domain: string;
      }[];
    };
    current_versions: string[];
    node_type: string;
    target_version: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        related_clusters: [] as IDataRow['cluster']['related_clusters'],
      },
      values.cluster,
    ),
    current_versions: values?.current_versions || ([] as string[]),
    node_type: values?.node_type || 'Backend',
    target_version: values?.target_version || '',
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_ids[0]].immute_domain,
            } as IDataRow['cluster'],
            // current_versions: infoItem.current_versions,
            node_type: infoItem.node_type,
            target_version: infoItem.target_version,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      current_versions: string[];
      node_type: string;
      target_version: string;
    }[];
  }>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const selected = computed(() =>
    formData.tableData
      .filter((item) => item.cluster.id)
      .flatMap((item) => [item.cluster, ...(item.cluster.related_clusters || [])]),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = async (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    const clusterIdList = clusterList.reduce<number[]>((prevList, listItem) => {
      prevList.push(listItem.id);
      return prevList;
    }, []);
    const relatedClusterResult = await findRelatedClustersByClusterIds({
      cluster_ids: clusterIdList,
    });
    const relatedClusterMap = relatedClusterResult.reduce<Record<string, string[]>>(
      (prev, item) =>
        Object.assign(prev, {
          [item.cluster_info.master_domain]: item.related_clusters.map((item) => item.master_domain),
        }),
      {},
    );
    const relatedClusterSet = new Set<string>();
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        const domain = item.master_domain;
        if (!selectedMap.value[domain] && !relatedClusterSet.has(domain)) {
          newList.push(
            createRowData({
              cluster: {
                cluster_type: item.cluster_type,
                cluster_type_name: item.cluster_type_name,
                id: item.id,
                master_domain: item.master_domain,
              } as IDataRow['cluster'],
            }),
          );
          relatedClusterMap[domain].forEach((mapItem) => relatedClusterSet.add(mapItem));
        }
        if (selectedMap.value[domain]) {
          relatedClusterMap[domain].forEach((mapItem) => relatedClusterSet.add(mapItem));
        }
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleNodeTypeBatchEdit = (value: string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: item.cluster.cluster_type === ClusterTypes.REDIS_INSTANCE ? 'Backend' : value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            cluster_ids: [
              tableItem.cluster.id,
              ...tableItem.cluster.related_clusters.map((relatedClusterItem) => relatedClusterItem.id),
            ],
            current_versions: tableItem.current_versions,
            node_type: tableItem.node_type,
            target_version: tableItem.target_version,
          })),
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
  .version-upgrade-page {
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
