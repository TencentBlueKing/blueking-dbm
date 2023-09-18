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
    class="details-reboot__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { BigDataRebootDetails, TicketDetails } from '@services/types/ticket';

  import { useCopy } from '@hooks';

  interface Props {
    ticketDetails: TicketDetails<BigDataRebootDetails>
  }

  const props = defineProps<Props>();

  const copy = useCopy();

  const { t } = useI18n();

  /**
   * 实例重启
   */

  const columns = [{
    label: t('集群ID'),
    field: 'cluster_id',
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
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('节点IP'),
    field: 'node_ip',
    render: ({ cell }: { cell: [] }) => cell.map((ip, index) => <p class="pt-2 pb-2">{ip}
      { index === 0
        ? <i v-bk-tooltips={t('复制IP')} class="db-icon-copy" onClick={() => copy(cell.join('\n'))} />
        : '' }
    </p>),
  }];

  const dataList = computed(() => {
    const list: any = [];
    const clusterId = props.ticketDetails?.details?.cluster_id;
    const clusters = props.ticketDetails?.details?.clusters?.[clusterId] || {};
    const nodeIp = props.ticketDetails?.details?.instance_list.map(k => k.ip) || [] ;
    list.push(Object.assign({
      cluster_id: clusterId, node_ip: nodeIp,
    }, clusters));
    return list;
  });
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
</style>
