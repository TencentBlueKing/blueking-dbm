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
        {{ item.isManulSelect ? t('从资源池手动选择') : t('从资源池自动匹配') }}
      </InfoItem>
      <InfoItem :label="t('缩容容量：')">
        {{ t('当前m_G_缩容后预估n_G', { m: item.totalDisk, n: item.totalDisk - item.shrinkDisk }) }}
      </InfoItem>
      <InfoItem :label="t('缩容数量：')">
        {{ t('n台', [item.count]) }}({{
          t('当前n台_缩容至m台', { n: item.totalHost, m: item.totalHost - item.count })
        }})
      </InfoItem>
      <InfoItem
        v-if="item.isManulSelect"
        :label="t('已选IP：')">
        <BkTable :data="item.hostList">
          <BkTableColumn
            field="ip"
            :label="t('节点 IP')" />
          <BkTableColumn
            field="bk_disk"
            :label="t('磁盘_GB')">
            <template #default="{ data: rowData }: { data: InfoData['hostList'][0] }">
              {{ hostInfoMap[rowData.ip] }}
            </template>
          </BkTableColumn>
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
    ticketDetails: TicketModel<Bigdata.ResourcePool.Shrink>;
  }

  interface InfoData {
    clusterId: number;
    clusterName: string;
    count: number;
    hostList: Bigdata.ResourcePool.Shrink['recycle_hosts'];
    isManulSelect: boolean;
    nodeText: string;
    shrinkDisk: number;
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
  let hostInfoMap: Record<string, number> = {};

  const dataList = computed(() => {
    const list: InfoData[] = [];
    const {
      cluster_id: clusterId,
      clusters,
      ext_info: extInfo,
      old_nodes: oldNodes,
      recycle_hosts: recycleHosts,
    } = props.ticketDetails.details;
    Object.entries(oldNodes).forEach(([node, hostList]) => {
      if (hostList.length > 0) {
        const extInfoData = extInfo[node as keyof Bigdata.ResourcePool.Shrink['ext_info']];
        const isManulSelect = recycleHosts?.length > 0;
        hostInfoMap = recycleHosts.reduce(
          (acc, host) => {
            Object.assign(acc, {
              [host.ip]: host.bk_disk,
            });
            return acc;
          },
          {} as Record<string, number>,
        );
        list.push({
          clusterId,
          clusterName: clusters[clusterId]?.immute_domain || '--',
          count: hostList.length,
          hostList: isManulSelect ? hostList : [],
          isManulSelect,
          nodeText: nodeTypeText[node] || '--',
          shrinkDisk: extInfoData.shrink_disk,
          totalDisk: extInfoData.total_disk,
          totalHost: extInfoData.total_hosts,
        });
      }
    });
    return list;
  });
</script>
