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
  <BkLoading :loading="isLoading">
    <InfoList>
      <InfoItem :label="t('集群：')">
        {{ rowData?.clusterName || '--' }}
      </InfoItem>
      <InfoItem :label="t('集群ID：')">
        {{ rowData?.clusterId || '--' }}
      </InfoItem>
      <template v-if="isScaleUp">
        <InfoItem :label="t('服务器选择方式：')">
          {{ isFromResourcePool ? t('从资源池匹配') : t('手动选择') }}
        </InfoItem>
        <template v-if="isFromResourcePool">
          <InfoItem :label="t('扩容规格：')">
            {{ rowData?.specName || '--' }}
          </InfoItem>
          <InfoItem :label="t('扩容数量：')">
            {{ t('n台', [rowData?.count]) || '--' }}
          </InfoItem>
        </template>
        <template v-else>
          <InfoItem
            :label="t('已选IP：')"
            style="width: 100%">
            <BkTable
              :columns="tableColumns"
              :data="ipList" />
          </InfoItem>
        </template>
      </template>
      <InfoItem
        v-else
        :label="t('缩容主机：')"
        style="width: 100%">
        <BkTable
          :columns="scaleDownTableColumns"
          :data="ticketDetails.details?.nodes" />
      </InfoItem>
    </InfoList>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type Riak } from '@services/model/ticket/ticket';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Riak.ScaleIn>
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

  const scaleDownTableColumns = [
    {
      field: 'ip',
      label: 'IP',
    },
  ];

  const ipList = computed(() => props.ticketDetails.details?.nodes?.riak || []);

  const { loading: isLoading } = useRequest(getResourceSpecList, {
    defaultParams: [{
      spec_cluster_type: 'riak',
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
