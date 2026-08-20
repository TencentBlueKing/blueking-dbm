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
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => row.spider_old_ip_list.map((item) => item.ip)"
      :min-width="150"
      :title="t('目标主机')">
      <template #default="{ row: data }: { row: RowData }">
        <p
          v-for="item in data.spider_old_ip_list"
          :key="item.ip">
          {{ item.ip }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="switch_spider_role"
      :min-width="150"
      :title="t('实例角色')">
      <template #default="{ row: data }: { row: RowData }">
        {{ roleLabelMap[data.switch_spider_role] }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="immute_domain"
      :min-width="150"
      :title="t('关联集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="150"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs[data.resource_spec[data.switch_spider_role]?.spec_id]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec[data.switch_spider_role]?.label_names?.length">
          <DbTag
            v-for="item in data.resource_spec[data.switch_spider_role]?.label_names"
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
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.is_safe ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderSwitchNodes>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const roleLabelMap = {
    spider_master: 'Spider Master',
    spider_slave: 'Spider Slave',
  } as Record<string, string>;
</script>
