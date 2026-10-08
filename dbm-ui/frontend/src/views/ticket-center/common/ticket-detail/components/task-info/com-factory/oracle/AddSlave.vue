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
  <InfoList>
    <InfoItem :label="t('上游类型')">
      {{ upstreamTypeLabel }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="index">
    <TicketInfoTableColumn
      col-key="upstream_instance"
      fixed="left"
      :min-width="210"
      :title="t('上游实例')">
      <template #default="{ row }: { row: IRowData }">
        <!-- master 模式：上游实例为 old_master（主库）；其余模式：上游实例为 old_node -->
        {{ formatInstanceAddress(isMasterUpstream ? row.old_master : row.old_node) }}
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
      v-if="isMasterUpstream"
      col-key="copy_source"
      :min-width="210"
      :title="t('复制源')">
      <template #default="{ row }: { row: IRowData }">
        <!-- master 模式：复制源为 old_node（从库） -->
        <span
          v-if="row.old_node"
          class="copy-source">
          <span class="copy-source__addr">{{ formatInstanceAddress(row.old_node) }}</span>
          <span class="copy-source__role">standby</span>
        </span>
        <span v-else>--</span>
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
            :class="{ 'is-notag': name === '通用无标签' }">
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

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type IRowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Oracle.oracleAddSlave>;
  }

  defineOptions({
    name: TicketTypes.ORACLE_ADD_SLAVE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();
  const { t } = useI18n();

  const upstreamTypeMap: Record<string, string> = {
    master: t('主库'),
    single: t('单节点'),
    slave: t('从库'),
  };

  // 上游类型：直接取协议 upstream_type，存量单据无该字段时展示 --
  const upstreamTypeLabel = computed(() => upstreamTypeMap[props.ticketDetails.details.upstream_type] || '--');

  // 仅上游类型为主库时展示复制源列
  const isMasterUpstream = computed(() => props.ticketDetails.details.upstream_type === 'master');

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
      color: #313238;
      font-family: 'JetBrains Mono', Consolas, monospace;
      font-size: 12px;
    }

    &__role {
      color: #979ba5;
      font-size: 12px;
    }
  }

  .detail-tag {
    display: inline-block;
    padding: 1px 8px;
    margin: 2px 2px 2px 0;
    border-radius: 2px;
    background: #eaebf0;
    color: #63656e;
    font-size: 12px;

    &.is-notag {
      background: #e1ecff;
      color: #3a84ff;
    }
  }
</style>
