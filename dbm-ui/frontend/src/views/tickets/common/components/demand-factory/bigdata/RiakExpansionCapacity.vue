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
    <div class="ticket-details__info">
      <div class="ticket-details__list">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('集群') }}：</span>
          <span class="ticket-details__item-value">{{ rowData?.clusterName || '--' }}</span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('集群ID') }}：</span>
          <span class="ticket-details__item-value">{{ rowData?.clusterId || '--' }}</span>
        </div>
        <template v-if="isScaleUp">
          <div class="ticket-details__item">
            <span class="ticket-details__item-label">{{ t('服务器选择方式') }}：</span>
            <span class="ticket-details__item-value">
              {{ isFromResourcePool ? t('从资源池匹配') : t('手动选择') }}
            </span>
          </div>
          <template v-if="isFromResourcePool">
            <div class="ticket-details__item">
              <span class="ticket-details__item-label">{{ t('扩容规格') }}：</span>
              <span class="ticket-details__item-value">{{ rowData?.specName || '--' }}</span>
            </div>
            <div class="ticket-details__item">
              <span class="ticket-details__item-label">{{ t('扩容数量') }}：</span>
              <span class="ticket-details__item-value">
                {{ t('n台', [rowData?.count]) || '--' }}
              </span>
            </div>
          </template>
          <template v-else>
            <div class="ticket-details__item table">
              <span class="ticket-details__item-label">{{ t('已选IP') }}：</span>
              <span class="ticket-details__item-value">
                <BkTable
                  :columns="tableColumns"
                  :data="ipList" />
              </span>
            </div>
          </template>
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
    clustersItems,
    TicketDetails,
  } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<{
      clusters: clustersItems
      cluster_id: number,
      ip_source: 'manual_input' | 'resource_pool',
      resource_spec: {
        riak: {
          count: number,
          spec_id: number
        }
      },
      nodes?: {
        riak: Array<{
          bk_cloud_id: number
          bk_host_id: number
          ip: string,
          alive: number,
          bk_disk: number,
        }>
      }
    }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const rowData = ref<{
    clusterName: string,
    clusterId: number,
    specName: string,
    count: number,
  }>();

  const isScaleUp = props.ticketDetails.ticket_type.includes('SCALE_OUT');
  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';
  const clusterId = props.ticketDetails.details.cluster_id;
  const clusterInfo = props.ticketDetails.details.clusters?.[clusterId] || {};

  const tableColumns = [
    {
      label: t('节点 IP'),
      field: 'ip',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: { data: { alive: number } }) => <span>{data.alive === 1 ? t('正常') : t('异常')}</span>,
    },
    {
      label: t('磁盘_GB'),
      field: 'bk_disk',
    },
  ];

  const ipList = computed(() => props.ticketDetails.details?.nodes?.riak || []);

  const { loading } = useRequest(getResourceSpecList, {
    defaultParams: [{
      spec_cluster_type: props.ticketDetails.group,
      offset: 0,
      limit: -1,
    }],
    onSuccess(specList) {
      const specListMap = specList.results.reduce((specListMapPrev, specItem) => Object.assign(specListMapPrev, {
        [specItem.spec_id]: specItem.spec_name,
      }), {} as Record<string, string>);

      rowData.value = {
        clusterId,
        count: props.ticketDetails.details?.resource_spec?.riak.count || 0,
        clusterName: clusterInfo?.immute_domain ?? '--',
        specName: specListMap[props.ticketDetails.details?.resource_spec?.riak.spec_id] || '--',
      };
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
