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
    class="mysql-cluster__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    MySQLOperationDetails,
    TicketDetails,
  } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<MySQLOperationDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type clusterItem = {
    cluster_ids: number[],
    immute_domain: string,
    name: string,
    cluster_type_name: string,
  }

  /**
   * 启用、禁用、删除
   */

  const columns = [{
    label: t('集群ID'),
    field: 'cluster_ids',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
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
  }, {
    label: t('集群类型'),
    field: 'cluster_type_name',
    render: ({ cell }: { cell: string }) => <span>{cell === 'tendbha' ? t('主从') : t('单节点')}</span>,
  }];

  const dataList = computed(() => {
    const list: clusterItem[] = [];
    const clusterIds = props.ticketDetails?.details?.cluster_ids;
    const clusters = props.ticketDetails?.details?.clusters || {};
    clusterIds?.forEach((item) => {
      const clusterData = clusters[item];
      list.push(Object.assign({
        cluster_ids: clusterData.id,
        cluster_type_name: clusterData.cluster_type_name,
        immute_domain: clusterData.immute_domain,
        name: clusterData.name,
      }));
    });
    return list;
  });
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
</style>
