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
    row-key="cluster_ids">
    <TicketInfoTableColumn
      col-key="cluster_ids"
      :get-copy-value="
        (item: RowData) => item.cluster_ids.map((clusterId) => ticketDetails.details.clusters[clusterId].immute_domain)
      "
      :min-width="200"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="old_master_slave"
      :min-width="150"
      :title="t('主从主机')">
      <template #default="{ row }: { row: RowData }">
        <div>
          <BkTag
            size="small"
            theme="info">
            M
          </BkTag>
          {{ row.display_info.old_master_slave[0] }}
        </div>
        <div>
          <BkTag
            size="small"
            theme="success">
            S
          </BkTag>
          {{ row.display_info.old_master_slave[1] }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="read_only_slaves"
      :min-width="150"
      :title="t('只读主机')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="host in row.read_only_slaves"
          :key="host.old_slave.bk_host_id">
          {{ host.old_slave.ip }}
        </div>
        <span v-if="row.read_only_slaves.length < 1"> -- </span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_version"
      :min-width="200"
      :title="t('当前版本')">
      <template #default="{ row }: { row: RowData }">
        <VersionContent
          :data="{
            version: row.display_info.current_version,
            package: row.display_info.current_package,
            charSet: row.display_info.charset,
            moduleName: row.display_info.current_module_name,
          }" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_version"
      :min-width="200"
      :title="t('目标版本')">
      <template #default="{ row }: { row: RowData }">
        <VersionContent
          :data="{
            version: row.display_info.target_version,
            package: row.display_info.target_package,
            charSet: row.display_info.charset,
            moduleName: row.display_info.target_module_name,
          }" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="new_master"
      :min-width="150"
      :title="t('新主从主机')">
      <template #default="{ row }: { row: RowData }">
        <div>
          <BkTag
            size="small"
            theme="info">
            M
          </BkTag>
          {{ row.resource_spec.new_master.hosts[0].ip }}
        </div>
        <div>
          <BkTag
            size="small"
            theme="success">
            S
          </BkTag>
          {{ row.resource_spec.new_slave.hosts[0].ip }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="new_read_only_slaves"
      :min-width="200"
      :title="t('新只读主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.read_only_slaves.length ? row.read_only_slaves.map((item) => item.new_slave.ip).join(',') : '--' }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.is_check_process ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('数据校验')">
      {{ ticketDetails.details.need_checksum ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('备份源：')">
      {{ backupSourceMap[ticketDetails.details.backup_source] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';
  import VersionContent from '../../mysql/components/VersionContent.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.MigrateUpgrade>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_MIGRATE_UPGRADE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const backupSourceMap = {
    local: t('本地备份'),
    remote: t('远程备份'),
  };
</script>
