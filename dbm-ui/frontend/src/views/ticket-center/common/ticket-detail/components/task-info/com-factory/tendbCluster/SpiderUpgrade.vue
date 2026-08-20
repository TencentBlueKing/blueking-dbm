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
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="200"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_version"
      :min-width="300"
      :title="t('当前版本')">
      <template #default="{ row }: { row: RowData }">
        <VersionContent
          :data="{
            version: row.current_version.db_version,
            package: row.current_version.pkg_name,
            charSet: row.current_version.charset,
            moduleName: row.current_version.db_module_name,
          }" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_version"
      :min-width="300"
      :title="t('目标版本')">
      <template #default="{ row }: { row: RowData }">
        <VersionContent
          :data="{
            version: row.target_version.db_version,
            package: row.target_version.pkg_name,
            charSet: row.target_version.charset,
            moduleName: row.target_version.db_module_name,
          }" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="150"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }">
        <p v-if="data.resource_spec.spider_master?.spec_id">
          {{ ticketDetails.details.specs[data.resource_spec.spider_master?.spec_id]?.name }}（spider_master）
        </p>
        <p v-else>--</p>
        <p v-if="data.resource_spec.spider_slave?.spec_id">
          {{ ticketDetails.details.specs[data.resource_spec.spider_slave?.spec_id]?.name }}（spider_slave）
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec.spider_master?.label_names?.length">
          <DbTag
            v-for="item in data.resource_spec.spider_master.label_names"
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
      {{ ticketDetails.details.is_check_process ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  import VersionContent from './components/VersionContent.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderUpgrade>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
