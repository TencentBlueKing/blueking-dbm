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
  <BkTable
    class="single-migrate-table"
    :data="tableData"
    :show-overflow="false">
    <BkTableColumn
      field="primary_key"
      fixed="left"
      :label="isDomain ? t('目标集群') : t('目标 Master 主机')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="(item, index) in data.primary_key"
          :key="index">
          {{ item }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="origin_old_nodes"
      :label="t('关联的主从实例')"
      min-width="400">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="(item, index) in data.instances"
          :key="index">
          <div class="domain-item">{{ item.domain }}</div>
          <div class="instance-item">--{{ item.master_ins }}</div>
          <div class="instance-item">--{{ item.slave_ins }}</div>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="spec_name"
      :label="t('规格')"
      :width="150">
    </BkTableColumn>
    <BkTableColumn
      field="db_version"
      :label="t('版本')"
      :width="200">
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.MigrateSingle>;
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

    let instances: ({ domain: string } & Redis.MigrateSingle['infos'][number]['src_cluster'][number])[] = [];
    if (item.display_info) {
      const oldNodesItem = item.old_nodes!;
      const masterItem = oldNodesItem.master[0];
      const slaveItem = oldNodesItem.slave[0];
      instances = [
        {
          cluster_id: item.cluster_id!,
          domain: clusters[item.cluster_id!].immute_domain,
          master_ins: `${masterItem.ip}:${masterItem.port}`,
          slave_ins: `${slaveItem.ip}:${slaveItem.port}`,
        },
      ];
    } else {
      instances = item.src_cluster.map((srcClusterItem) => ({
        domain: clusters[srcClusterItem.cluster_id].immute_domain,
        ...srcClusterItem,
      }));
    }
    return {
      db_version: item.db_version,
      instances,
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
