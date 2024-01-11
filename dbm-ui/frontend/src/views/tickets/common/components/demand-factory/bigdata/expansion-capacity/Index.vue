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
  <BkLoading :loading="loading">
    <div
      v-for="(item, index) in dataList"
      :key="index"
      class="ticket-details__info">
      <strong class="ticket-details__info-title">{{ item.title }}</strong>
      <div
        class="ticket-details__list">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('集群') }}：</span>
          <span class="ticket-details__item-value">{{ item.clusterName }}</span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('集群ID') }}：</span>
          <span class="ticket-details__item-value">{{ item.clusterId }}</span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('服务器选择方式') }}：</span>
          <span class="ticket-details__item-value">{{ isFromResourcePool ? t('从资源池匹配') : t('手动选择') }} </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ isScaleUp ? t('扩容容量') : t('缩容容量') }}：</span>
          <span class="ticket-details__item-value">
            {{ isScaleUp ? item.targetDisk : item.shrinkDisk }}GB
            （{{ isScaleUp ?
              t('当前m_G_扩容后预估n_G', {m: item.totalDisk, n: item.expectDisk})
              : t('当前m_G_缩容后预估n_G', {m: item.totalDisk, n: item.totalDisk - item.shrinkDisk})
            }}）
          </span>
        </div>
        <template v-if="isFromResourcePool">
          <div class="ticket-details__item">
            <span class="ticket-details__item-label">{{ isScaleUp ? t('扩容规格') : t('缩容规格') }}：</span>
            <span class="ticket-details__item-value">{{ item.specName }}</span>
          </div>
          <div class="ticket-details__item">
            <span class="ticket-details__item-label">{{ isScaleUp ? t('扩容数量') : t('缩容数量') }}：</span>
            <span class="ticket-details__item-value">
              {{ t('n台', [item.count]) }}（{{ t('当前n台_扩容至m台', {n: item.totalHost, m: item.totalHost + item.count}) }})
            </span>
          </div>
        </template>
        <template v-else>
          <div class="ticket-details__item">
            <span class="ticket-details__item-label">{{ t('已选IP') }}：</span>
          </div>
          <div class="inline-table">
            <SelectIpTable :data="item.hostList" />
          </div>
        </template>
      </div>
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import type {
    BigDataCapacityDetails,
    TicketDetails,
  } from '@services/types/ticket';

  import SelectIpTable from './SelectIpTable.vue';

  interface Props {
    ticketDetails: TicketDetails<BigDataCapacityDetails>
  }

  interface RowData {
    title: string,
    clusterName: string,
    clusterId: string,
    totalDisk: number,
    targetDisk: number,
    expectDisk: number,
    shrinkDisk: number,
    specName: string,
    totalHost: number,
    count: number,
    hostList: {
      ip: string,
      alive: number,
      bk_disk: number,
      instance_num: number,
    }[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList = ref<RowData[]>([]);

  const nodeTypeText: Record<string, string> = {
    hot: t('热节点'),
    cold: t('冷节点'),
    master: 'Master',
    client: 'Client',
    datanode: 'DataNode',
    namenode: 'NameNode',
    zookeeper: 'Zookeeper',
    broker: 'Broker',
    proxy: 'Proxy',
    slave: 'Slave',
    bookkeeper: 'Bookkeeper',
  };
  const isScaleUp = props.ticketDetails.ticket_type.includes('SCALE_UP');
  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';
  const clusterId = props.ticketDetails.details.cluster_id;
  const clusterInfo = props.ticketDetails.details.clusters?.[clusterId] || {};
  const extInfo = props.ticketDetails.details.ext_info;

  const { loading } = useRequest(getResourceSpecList, {
    defaultParams: [{
      spec_cluster_type: props.ticketDetails.group,
      offset: 0,
      limit: -1,
    }],
    onSuccess: async (res) => {
      const specListMap = res.results.reduce((obj, item) => {
        Object.assign(obj, {
          [item.spec_id]: item.spec_name,
        });
        return obj;
      }, {} as Record<string, string>);

      const generateDataRow = (key: string, id: number, count: number) => ({
        clusterId,
        count,
        title: nodeTypeText[key],
        clusterName: clusterInfo?.immute_domain ?? '--',
        totalDisk: extInfo[key].total_disk,
        targetDisk: extInfo[key].target_disk,
        expectDisk: extInfo[key].expansion_disk,
        shrinkDisk: extInfo[key].shrink_disk,
        totalHost: extInfo[key].total_hosts,
        hostList: extInfo[key].host_list,
        specName: specListMap[id],
      }) as unknown as RowData;

      const targetObj = isFromResourcePool
        ? props.ticketDetails.details.resource_spec : props.ticketDetails.details.nodes;
      dataList.value = Object.entries(targetObj).map(([key, item]) => ({
        ...generateDataRow(key, item.spec_id, item.count),
      }));
    },
  });
</script>

<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";

  .inline-table {
    padding-left: 160px;
    margin-top: -24px;
  }
</style>
