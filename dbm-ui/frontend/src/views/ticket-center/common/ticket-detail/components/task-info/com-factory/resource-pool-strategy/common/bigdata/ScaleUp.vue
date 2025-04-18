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
      <InfoItem :label="t('集群')">
        {{ item.clusterName }}
      </InfoItem>
      <InfoItem :label="t('集群ID')">
        {{ item.clusterId }}
      </InfoItem>
      <InfoItem :label="t('服务器选择方式')">
        {{ item.isManulSelect ? t('从资源池手动选择') : t('从资源池自动匹配') }}
      </InfoItem>
      <InfoItem :label="t('扩容容量')">
        {{ t('当前m_G_扩容后预估n_G', { m: item.totalDisk, n: item.expectDisk }) }}
      </InfoItem>
      <InfoItem :label="t('扩容数量')">
        {{ t('n台', [item.count]) }}({{
          t('当前n台_扩容至m台', { n: item.totalHost, m: item.totalHost + item.count })
        }})
      </InfoItem>
      <InfoItem
        v-if="item.isManulSelect"
        :label="t('已选IP')">
        <BkTable :data="item.hostList">
          <BkTableColumn
            field="ip"
            :label="t('节点 IP')" />
          <BkTableColumn
            field="bk_disk"
            :label="t('磁盘容量(G)')" />
        </BkTable>
      </InfoItem>
      <InfoItem
        v-else
        :label="t('匹配规格')">
        {{ item.specName }}
      </InfoItem>
    </InfoList>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Bigdata } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Bigdata.ResourcePool.ScaleUp>;
  }

  interface RowData {
    clusterId: number;
    clusterName: string;
    count: number;
    expectDisk: number;
    hostList: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_disk: number;
      bk_host_id: number;
      ip: string;
    }[];
    isManulSelect: boolean;
    nodeText: string;
    specName: string;
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
    const {
      cluster_id: clusterId,
      clusters,
      ext_info: extInfo,
      resource_spec: resourceSpec,
      specs,
    } = props.ticketDetails.details;
    Object.entries(resourceSpec).forEach(([node, currentResourceSpec]) => {
      if (currentResourceSpec) {
        const extInfoData = extInfo[node as keyof Bigdata.ResourcePool.Shrink['ext_info']];
        const isManulSelect = currentResourceSpec.hosts?.length > 0;
        list.push({
          clusterId,
          clusterName: clusters[clusterId]?.immute_domain || '--',
          count: currentResourceSpec.count,
          expectDisk: extInfoData.expansion_disk,
          hostList: isManulSelect ? currentResourceSpec.hosts : [],
          isManulSelect,
          nodeText: nodeTypeText[node] || '--',
          specName: specs[currentResourceSpec.spec_id]?.name || '--',
          totalDisk: extInfoData.total_disk,
          totalHost: extInfoData.total_hosts,
        });
      }
    });
    return list;
  });
</script>
