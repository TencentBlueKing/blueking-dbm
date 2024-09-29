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

  import TicketModel, {type Redis} from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
    inheritAttrs: false
  })

  const { t } = useI18n();

  const { clusters, infos } = props.ticketDetails.details;
  const dataList: (Props['ticketDetails']['details']['infos'][number] & Props['ticketDetails']['details']['clusters'][number])[] = [];
  infos.forEach(infoItem => {
    infoItem.cluster_ids.forEach((clusterId) => {
      dataList.push(Object.assign({}, infoItem, clusters[clusterId]));
    });
  })

  const columns = [
    {
      label: t('目标集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('架构版本'),
      field: 'cluster_type_name',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('节点类型'),
      field: 'node_type',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('当前使用的版本'),
      field: 'current_versions',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string[] }) => <span>{cell.length > 0 ? cell.join(',') : '--'}</span>,
    },
    {
      label: t('目标版本'),
      field: 'target_version',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
  ];
</script>
