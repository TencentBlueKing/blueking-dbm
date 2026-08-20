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
      :title="t('目标集群')"
      :width="350">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </p>
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
      :min-width="300"
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
      col-key="spec_id"
      :min-width="120"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.backend_group.spec_id]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec.backend_group?.label_names?.length">
          <DbTag
            v-for="item in data.resource_spec.backend_group.label_names"
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
      col-key="read_only_slaves"
      :min-width="400"
      :title="t('只读主机（旧 -> 新）')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.read_only_slaves"
          :key="item.old_slave.ip">
          <div class="origin-readonly-host">
            <div class="readonly-host-info origin-readonly-host-info">
              {{ item.old_slave.ip }}（{{ item.old_slave.bk_sub_zone || '--' }}）
            </div>
            <div class="origin-readonly-host-arrow">-></div>
            <div class="readonly-host-info">{{ item.new_slave.ip }}（{{ item.new_slave.bk_sub_zone || '--' }}）</div>
          </div>
        </div>
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
<style lang="less" scoped>
  .origin-readonly-host {
    display: flex;
    line-height: 28px;

    .readonly-host-info {
      white-space: nowrap;
      text-align: end;
      font-size: 12px;
      padding: 0 8px;
    }

    .origin-readonly-host-info {
      color: #979ba5;
      background: #fafbfd;
    }

    .origin-readonly-host-arrow {
      width: 15px;
    }
  }
</style>
