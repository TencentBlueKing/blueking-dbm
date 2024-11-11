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
    :data="tableData" />
  <div class="ticket-details-item">
    <span class="ticket-details-item-label">{{ t('备份源') }}：</span>
    <span class="ticket-details-item-value">
      {{ props.ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </span>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { SpiderMigrateCluster } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';
  import { checkInstance } from '@services/source/dbbase';

  interface Props {
    ticketDetails: TicketModel<SpiderMigrateCluster>
  }

  interface IDataRow {
    oldMasterIp: string,
    oldMasterRelatedInstance: string[],
    oldSlaveIp: string,
    oldSlaveRelatedInstance: string[],
    clusterDomain: string,
    clusterName: string,
    newIps: string
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('目标主库主机'),
      field: 'oldMasterIp',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('主库主机关联实例'),
      field: 'oldMasterRelatedInstance',
      render: ({ data }: { data: IDataRow }) => data.oldMasterRelatedInstance.map((item: string) => <p class="mb-4">{item}</p>),
    },
    {
      label: t('目标从库主机'),
      field: 'oldSlaveIp',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('从库主机关联实例'),
      field: 'oldSlaveRelatedInstance',
      render: ({ data }: { data: IDataRow }) => data.oldSlaveRelatedInstance.map((item: string) => <p class="mb-4">{item}</p>),
    },
    {
      label: t('集群名称'),
      showOverflowTooltip: false,
      render: ({ data }: { data: IDataRow }) => (
        <div class="cluster-name text-overflow"
          v-overflow-tips={{
            content: `
                    <p>${t('域名')}：${data.clusterDomain}</p>
                    ${data.clusterName ? `<p>${('集群别名')}：${data.clusterName}</p>` : null}
                  `,
            allowHTML: true,
          }}>
          <span>{data.clusterDomain}</span><br />
          <span class="cluster-name__alias">{data.clusterName}</span>
        </div>
      ),
    },
    {
      label: t('新实例'),
      field: 'newIps',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
  ];

  const tableData = shallowRef<IDataRow[]>([]);

  watch(
    () => props.ticketDetails.details,
    async () => {
      const { infos, clusters } = props.ticketDetails.details;
      const oldIps = infos.flatMap(info => [info.old_master.ip, info.old_slave.ip]);

      const instanceList = await checkInstance({
        instance_addresses: oldIps,
        bk_biz_id: props.ticketDetails.bk_biz_id,
      });

      const instancesByIp = instanceList.reduce<Record<string, string[]>>((acc, { ip, instance_address }) => {
        acc[ip] = acc[ip] || [];
        acc[ip].push(instance_address);
        return acc;
      }, {});

      tableData.value = infos.map(info => ({
        oldMasterIp: info.old_master.ip,
        oldMasterRelatedInstance: instancesByIp[info.old_master.ip],
        oldSlaveIp: info.old_slave.ip,
        oldSlaveRelatedInstance: instancesByIp[info.old_slave.ip],
        clusterDomain: clusters[info.cluster_id].immute_domain,
        clusterName: clusters[info.cluster_id].name,
        newIps: `${info.new_master.ip}, ${info.new_slave.ip}`,
      }));
    },
    {
      immediate: true,
    }
  );
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
