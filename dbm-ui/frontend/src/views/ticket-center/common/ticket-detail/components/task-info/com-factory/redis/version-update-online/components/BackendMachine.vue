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
    :data="dataList"
    row-key="ip">
    <TicketInfoTableColumn
      col-key="ip"
      fixed="left"
      :get-copy-value="(row: RowData) => [row.ip, row.pair_machine.ip]"
      :min-width="250"
      :title="t('目标主机')">
      <template #default="{ row }: { row : RowData }">
        <div>
          {{ row.ip }}
        </div>
        <div
          v-if="row.pair_machine.ip"
          style="color: #979ba5">
          {{ t('关联 Slave') }}: {{ row.pair_machine.ip }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="instance_role"
      :title="t('角色类型')"
      :width="200">
      <template #default="{ row }: { row : RowData }">
        <div class="role-item">
          {{ row.instance_role ? row.instance_role.split('_')[1] : '' }}
        </div>
        <div
          v-if="row.pair_machine.ip"
          class="role-item">
          slave
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="related_clusters"
      :title="t('所属集群')"
      :width="200">
      <template #default="{ row }: { row : RowData }">
        <div
          v-for="item in row.related_clusters"
          :key="item">
          {{ item }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_versions"
      :min-width="250"
      :title="t('当前版本')">
      <template #default="{ row }: { row : RowData }">
        <div
          v-for="item in row.current_versions"
          :key="item">
          {{ item }}
        </div>
        <div
          v-for="item in row.pair_machine.slave_current_versions"
          :key="item">
          {{ item }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_version"
      :min-width="250"
      :title="t('目标版本')">
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  type RowData = {
    current_versions: string[];
    instance_role: string;
    ip: string;
    pair_machine: {
      ip: string;
      slave_current_versions: string[];
    };
    related_clusters: string[];
    target_version: string;
  };

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;

  // 集群维度转换成IP维度, 分主从
  const ipMap: Record<string, RowData> = {};
  const pairSlaveIpMap: Record<string, boolean> = {};
  infos.forEach((infoItem) => {
    infoItem.target_versions.forEach((targetItem) => {
      if (pairSlaveIpMap[targetItem.ip]) {
        return;
      }

      ipMap[targetItem.ip] = {
        current_versions: infoItem.current_versions,
        instance_role: targetItem.instance_role || 'redis_master',
        ip: targetItem.ip,
        pair_machine: {
          ip: targetItem.slave_ip || '',
          slave_current_versions: infoItem.slave_current_versions || [],
        },
        related_clusters: targetItem.related_clusters,
        target_version: targetItem.version,
      };
      if (targetItem.slave_ip) {
        pairSlaveIpMap[targetItem.slave_ip] = true;
      }
    });
  });

  const dataList = Object.values(ipMap);
</script>
