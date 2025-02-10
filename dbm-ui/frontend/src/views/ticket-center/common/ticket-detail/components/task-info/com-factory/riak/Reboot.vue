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

  import TicketModel, { type Riak } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

   import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Riak.Reboot>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.RIAK_CLUSTER_REBOOT,
    inheritAttrs: false
  })

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
      <div>
        <span>{data.immute_domain}</span>
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
            onClick={() => execCopy(cell, t('复制成功，共n条', { n: 1 }))} />
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
