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
    <strong class="ticket-details-info-title">{{ item.title }}</strong>
    <InfoList>
      <InfoItem :label="t('集群：')">
        {{ item.clusterName }}
      </InfoItem>
      <InfoItem :label="t('集群ID：')">
        {{ item.clusterId }}
      </InfoItem>
      <InfoItem :label="t('服务器选择方式：')">
        {{ t('从资源池手动选择') }}
      </InfoItem>
      <InfoItem :label="t('扩容容量：')">
        {{ t('当前m_G_扩容后预估n_G', { m: item.totalDisk, n: item.expectDisk }) }}
      </InfoItem>
      <InfoItem :label="t('扩容数量：')">
        {{ t('n台', [item.count]) }}({{
          t('当前n台_扩容至m台', { n: item.totalHost, m: item.totalHost + item.count })
        }})
      </InfoItem>
      <InfoItem :label="t('已选IP：')">
        <SelectIpTable :data="item.hostList" />
      </InfoItem>
    </InfoList>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Bigdata } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  import SelectIpTable from './SelectIpTable.vue';

  interface Props {
    ticketDetails: TicketModel<Bigdata.ResourcePool.ScaleUp>;
  }

  interface RowData {
    clusterId: number;
    clusterName: string;
    count: number;
    expectDisk: number;
    hostList: {
      alive: number;
      bk_disk: number;
      instance_num?: number;
      ip: string;
    }[];
    shrinkDisk: number;
    title: string;
    totalDisk: number;
    totalHost: number;
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
    const { cluster_id: clusterId, clusters, ext_info: extInfo } = props.ticketDetails.details;
    const clusterInfo = clusters?.[clusterId] || {};
    for (const [key, item] of Object.entries(props.ticketDetails.details.resource_spec)) {
      if (item.hosts.length) {
        const extInfoData = extInfo[key as keyof Bigdata.ResourcePool.ScaleUp['ext_info']];
        list.push({
          clusterId,
          clusterName: clusterInfo?.immute_domain ?? '--',
          count: item.count,
          expectDisk: extInfoData.expansion_disk,
          hostList: extInfoData.host_list.map((item) => ({
            alive: item.agent_status,
            bk_disk: item.bk_disk,
            ip: item.ip,
          })),
          shrinkDisk: extInfoData.shrink_disk,
          title: nodeTypeText[key],
          totalDisk: extInfoData.total_disk,
          totalHost: extInfoData.total_hosts,
        });
      }
    }
    return list;
  });
</script>
