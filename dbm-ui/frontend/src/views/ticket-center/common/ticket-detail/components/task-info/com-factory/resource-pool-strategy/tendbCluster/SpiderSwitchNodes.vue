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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="cluster_id">
    <TableColumn
      :min-width="150"
      :title="t('目标主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.spider_old_ip_list[0].ip }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="150"
      :title="t('关联实例')">
      <template #default="{ row: data }: { row: RowData }">
        {{ `${data.spider_old_ip_list[0].ip}:${data.spider_old_ip_list[0].port}` }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="150"
      :title="t('实例角色')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.switch_spider_role }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="150"
      :title="t('关联集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="150"
      :title="t('目标规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{
          ticketDetails.details.specs[
            data.resource_spec[`${data.switch_spider_role}_${data.spider_old_ip_list[0].ip}`].spec_id
          ].name
        }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template
          v-if="data.resource_spec[`${data.switch_spider_role}_${data.spider_old_ip_list[0].ip}`]?.label_names?.length">
          <BkTag
            v-for="item in data.resource_spec.new_slave.label_names"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <BkTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </BkTag>
      </template>
    </TableColumn>
  </PrimaryTable>
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

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderSwitchNodes>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];
</script>
