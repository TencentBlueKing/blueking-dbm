<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="index">
    <TicketInfoTableColumn
      col-key="old_node"
      fixed="left"
      :min-width="190"
      :title="t('被替换主机')">
      <template #default="{ row }: { row: IRowData }">
        {{ row.replace_host?.ip || row.old_node?.ip || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="role"
      :min-width="110"
      :title="t('角色')">
      <template #default="{ row }: { row: IRowData }">
        {{ row.old_node.role || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="replication_source"
      :min-width="210"
      :title="t('复制源')">
      <template #default="{ row }: { row: IRowData }">
        <span
          v-if="row.old_node"
          class="copy-source">
          <span class="copy-source__addr">{{ formatInstanceAddress(row.old_node) }}</span>
          <span class="copy-source__role">{{ row.old_node.role || '--' }}</span>
        </span>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_id"
      :min-width="220"
      :title="t('所属集群')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type"
      :min-width="110"
      :title="t('集群类型')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters?.[row.cluster_id]?.cluster_type_name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="200"
      :title="t('目标规格')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.specs?.[row.resource_spec?.oracle?.spec_id]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="labels"
      :min-width="210"
      :title="t('资源标签')">
      <template #default="{ row }: { row: IRowData }">
        <template v-if="row.resource_spec?.oracle?.label_names?.length">
          <span
            v-for="(name, i) in row.resource_spec.oracle.label_names"
            :key="i"
            class="detail-tag"
            :class="{ 'is-notag': name === t('通用无标签') }">
            {{ name }}
          </span>
        </template>
        <span
          v-else
          class="detail-tag is-notag">
          {{ t('通用无标签') }}
        </span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type TicketModel from '@services/model/ticket/ticket';
  import type { Oracle } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type IRowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Oracle.oracleReplaceHost>;
  }

  defineOptions({
    name: TicketTypes.ORACLE_REPLACE_HOST,
    inheritAttrs: false,
  });

  defineProps<Props>();
  const { t } = useI18n();

  // 协议 old_node/old_master 携带 port，展示 ip:port；兼容无 port 的存量单据仅展示 ip
  const formatInstanceAddress = (host?: { ip: string; port?: number }) => {
    if (!host?.ip) {
      return '--';
    }
    return host.port ? `${host.ip}:${host.port}` : host.ip;
  };
</script>

<style lang="less" scoped>
  .copy-source {
    display: inline-flex;
    column-gap: 8px;
    align-items: baseline;

    &__addr {
      font-family: 'JetBrains Mono', Consolas, monospace;
      font-size: 12px;
      color: #313238;
    }

    &__role {
      font-size: 12px;
      color: #979ba5;
    }
  }

  .detail-tag {
    display: inline-block;
    padding: 1px 8px;
    margin: 2px 2px 2px 0;
    font-size: 12px;
    color: #63656e;
    background: #eaebf0;
    border-radius: 2px;

    &.is-notag {
      color: #3a84ff;
      background: #e1ecff;
    }
  }
</style>
