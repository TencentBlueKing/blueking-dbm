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
  <div
    v-for="(item, index) in dataList"
    :key="index">
    <strong class="ticket-details-info-title">{{ item.nodeText }}</strong>
    <InfoList>
      <InfoItem :label="t('集群：')">
        {{ item.clusterName }}
      </InfoItem>
      <InfoItem :label="t('集群ID：')">
        {{ item.clusterId }}
      </InfoItem>
      <InfoItem :label="t('服务器选择方式：')">
        {{ item.ipSourceDisplay }}
      </InfoItem>
      <InfoItem :label="t('已选IP：')">
        <BkTable :data="item.hostList">
          <BkTableColumn
            field="oldNodeIp"
            :label="t('被替换的节点IP')" />
          <BkTableColumn
            field="newNodeIp"
            :label="t('新节点IP')" />
        </BkTable>
      </InfoItem>
    </InfoList>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Bigdata } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Bigdata.ResourcePool.Replace>;
  }

  interface RowData {
    clusterId: number;
    clusterName: string;
    hostList: {
      newNodeIp: string;
      oldNodeIp: string;
    }[];
    ipSourceDisplay: string;
    nodeText: string;
  }

  const props = defineProps<Props>();

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

  const dataList = computed(() => {
    const list: RowData[] = [];
    const { cluster_id: clusterId, clusters, resource_spec: resourceSpec, specs } = props.ticketDetails.details;
    Object.entries(props.ticketDetails.details.old_nodes).forEach(([node, hosts]) => {
      if (hosts.length) {
        const currentResourceSpec = resourceSpec[node as keyof typeof resourceSpec];
        const isManulSelect = currentResourceSpec.hosts?.length > 0;
        list.push({
          clusterId,
          clusterName: clusters[clusterId]?.immute_domain || '--',
          hostList: hosts.map((host: { ip: string }) => {
            return {
              newNodeIp: isManulSelect
                ? currentResourceSpec.hosts[0].ip
                : `${t('匹配规格：')} ${specs[currentResourceSpec.spec_id].name}`,
              oldNodeIp: host.ip,
            };
          }),
          ipSourceDisplay: isManulSelect ? t('从资源池手动选择') : t('从资源池自动匹配'),
          nodeText: nodeTypeText[node] || '--',
        });
      }
    });
    return list;
  });
</script>
