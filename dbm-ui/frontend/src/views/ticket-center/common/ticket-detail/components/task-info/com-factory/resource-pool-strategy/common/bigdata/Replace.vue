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
  <BkTable :data="[ticketDetails.details]">
    <BkTableColumn
      field="cluster_id"
      :label="t('集群ID')" />
    <BkTableColumn
      field="immute_domain"
      :label="t('集群名称')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="cluster_type_name"
      :label="t('集群类型')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('角色类型')">
      <template #default="{ data }: { data: RowData }">
        {{ nodeTypeText[getCurrentNode(data.old_nodes)] }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('新节点IP')">
      <template #default="{ data }: { data: RowData }">
        {{ data.resource_spec[getCurrentNode(data.old_nodes) as keyof RowData['old_nodes']].hosts[0].ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('被替换的节点IP')">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes[getCurrentNode(data.old_nodes) as keyof RowData['old_nodes']][0].ip }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Bigdata } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Bigdata.ResourcePool.Replace>;
  }

  type RowData = Props['ticketDetails']['details'];

  defineProps<Props>();

  const { t } = useI18n();

  const nodeTypeText: Record<string, string> = {
    bookkeeper: 'Bookkeeper',
    broker: 'Broker',
    client: 'Client',
    cold: t('冷节点'),
    datanode: 'DataNode',
    hot: t('热节点'),
    master: 'Master',
    namenode: 'NameNode',
    proxy: 'Proxy',
    slave: 'Slave',
    zookeeper: 'Zookeeper',
  };

  const getCurrentNode = (nodes: RowData['old_nodes']) => {
    let currentNode = '';
    Object.entries(nodes).forEach(([key, item]) => {
      if (item.length) {
        currentNode = key;
      }
    });
    return currentNode;
  };
</script>
