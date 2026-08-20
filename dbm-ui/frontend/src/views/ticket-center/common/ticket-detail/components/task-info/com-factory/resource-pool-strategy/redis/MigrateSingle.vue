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
  <TicketInfoTable
    class="single-migrate-table"
    :data="tableData"
    row-key="primary_key">
    <TicketInfoTableColumn
      col-key="primary_key"
      fixed="left"
      :get-copy-value="(row: RowData) => row.primary_key"
      :title="isDomain ? t('目标集群') : t('目标 Master 主机')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="(item, index) in row.primary_key"
          :key="index">
          {{ item }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="origin_old_nodes"
      min-width="400"
      :title="t('关联的主从实例')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="(item, index) in row.instances"
          :key="index">
          <div class="domain-item">{{ item.domain }}</div>
          <div class="instance-item">--{{ item.master_ins }}</div>
          <div class="instance-item">--{{ item.slave_ins }}</div>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_name"
      :title="t('规格')"
      :width="150">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.label_names.length">
          <DbTag
            v-for="item in row.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_version"
      :title="t('版本')"
      :width="200">
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.MigrateSingle>;
  }

  type RowData = (typeof tableData)[number];

  defineOptions({
    name: TicketTypes.REDIS_SINGLE_INS_MIGRATE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos, specs } = props.ticketDetails.details;
  const isDomain = (infos[0].display_info?.migrate_type || infos[0].migrate_type) === 'domain';

  const tableData = props.ticketDetails.details.infos.map((item) => {
    const primaryKey = isDomain
      ? item.display_info?.domain || item.migrate_domain
      : item.display_info?.ip || item.migrate_ip;
    const specName = specs[item.resource_spec.backend_group.spec_id].name;

    let instances: ({ domain: string } & Redis.ResourcePool.MigrateSingle['infos'][number]['src_cluster'][number])[] =
      [];
    if (item.display_info) {
      const oldNodesItem = item.old_nodes!;
      const masterItem = oldNodesItem.master[0];
      const slaveItem = oldNodesItem.slave[0];
      if (masterItem && slaveItem) {
        instances = [
          {
            cluster_id: item.cluster_id!,
            domain: clusters[item.cluster_id!]?.immute_domain,
            master_ins: `${masterItem.ip}:${masterItem.port}`,
            slave_ins: `${slaveItem.ip}:${slaveItem.port}`,
          },
        ];
      }
    } else {
      instances = item.src_cluster.map((srcClusterItem) => ({
        domain: clusters[srcClusterItem.cluster_id].immute_domain,
        ...srcClusterItem,
      }));
    }
    return {
      db_version: item.db_version,
      instances,
      label_names: item.resource_spec.backend_group.label_names || [],
      primary_key: primaryKey?.split(',') || '',
      spec_name: specName,
    };
  });
</script>

<style lang="less" scoped>
  .single-migrate-table {
    .domain-item {
      color: #4d4f56;
    }

    .instance-item {
      color: #979ba5;
    }
  }
</style>
