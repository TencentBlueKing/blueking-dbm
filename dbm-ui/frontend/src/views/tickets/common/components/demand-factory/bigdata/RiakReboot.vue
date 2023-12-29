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
  <DbOriginalTable
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    clustersItems,
    TicketDetails,
  } from '@services/types/ticket';

  import { useCopy } from '@hooks';

  interface Props {
    ticketDetails: TicketDetails<{
      clusters: clustersItems,
      cluster_id: number,
      bk_cloud_id: number,
      bk_host_id: number,
      ip: string
    }>
  }

  const props = defineProps<Props>();

  const copy = useCopy();
  const { t } = useI18n();

  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: any }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.immute_domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.immute_domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
    },
    {
      label: t('集群类型'),
      field: 'cluster_type_name',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('节点IP'),
      field: 'node_ip',
      render: ({ cell }: { cell: string }) => (
        <p class="pt-2 pb-2">{cell}
          <db-icon
            v-bk-tooltips={t('复制IP')}
            type="copy"
            onClick={() => copy(cell)} />
        </p>
      ),
    },
  ];

  const dataList = computed(() => {
    const clusterId = props.ticketDetails?.details?.cluster_id;
    const clusters = props.ticketDetails?.details?.clusters?.[clusterId] || {};

    return [{
      cluster_id: clusterId,
      immute_domain: clusters.immute_domain,
      cluster_type_name: clusters.cluster_type_name,
      name: clusters.name,
      node_ip: props.ticketDetails?.details?.ip,
    }];
  });
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
</style>
