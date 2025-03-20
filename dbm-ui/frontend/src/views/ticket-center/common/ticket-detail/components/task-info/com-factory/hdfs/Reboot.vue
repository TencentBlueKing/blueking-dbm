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

  import TicketModel, { type Hdfs } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Hdfs.Reboot>;
  }

  defineOptions({
    name: TicketTypes.HDFS_REBOOT,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  /**
   * 实例重启
   */

  const columns = [
    {
      field: 'cluster_id',
      label: t('集群ID'),
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      field: 'immute_domain',
      label: t('集群名称'),
      render: ({ data }: { data: any }) => data.immute_domain,
      showOverflowTooltip: false,
    },
    {
      field: 'cluster_type_name',
      label: t('集群类型'),
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      field: 'node_ip',
      label: t('节点IP'),
      render: ({ cell }: { cell: [] }) =>
        cell.map((ip, index) => (
          <p class='pt-2 pb-2'>
            {ip}
            {index === 0 ? (
              <i
                v-bk-tooltips={t('复制IP')}
                class='db-icon-copy'
                onClick={() => execCopy(cell.join('\n'), t('复制成功，共n条', { n: cell.length }))}
              />
            ) : (
              ''
            )}
          </p>
        )),
    },
  ];

  const dataList = computed(() => {
    const list: any = [];
    const clusterId = props.ticketDetails?.details?.cluster_id;
    const clusters = props.ticketDetails?.details?.clusters?.[clusterId] || {};
    const nodeIp = props.ticketDetails?.details?.instance_list.map((k) => k.ip) || [];
    list.push(
      Object.assign(
        {
          cluster_id: clusterId,
          node_ip: nodeIp,
        },
        clusters,
      ),
    );
    return list;
  });
</script>
