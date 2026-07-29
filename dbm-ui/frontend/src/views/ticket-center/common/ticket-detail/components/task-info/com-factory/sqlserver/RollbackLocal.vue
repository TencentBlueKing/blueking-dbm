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
  <InfoList>
    <InfoItem :label="t('回档方式')">
      <strong>
        {{ ticketDetails.details.infos[0]?.restore_time ? t('指定时间回档') : t('指定备份记录回档') }}
      </strong>
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="src_cluster">
    <TicketInfoTableColumn
      col-key="src_cluster"
      fixed="left"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.src_cluster].immute_domain"
      :title="t('源集群')"
      :width="220">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      v-if="ticketDetails.details.infos[0]?.restore_time"
      col-key="restore_time"
      :title="t('指定时间')"
      :width="180">
      <template #default="{ row: data }: { row: RowData }">
        {{ utcDisplayTime(data.restore_time) }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="backup_record"
      :title="t('备份记录')"
      :width="380">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.restore_backup_file">
          <div class="content-block">
            <div class="content-label">{{ t('备份时间 ：') }}</div>
            <div class="content-value">{{ utcDisplayTime(data.restore_backup_file.end_time) }}</div>
            <div class="content-label">{{ t('备份角色 ：') }}</div>
            <div class="content-value">{{ data.restore_backup_file.role }}</div>
            <div class="content-label">{{ t('备份 ID ：') }}</div>
            <div class="content-value">{{ data.restore_backup_file.backup_id || '--' }}</div>
            <div class="content-label">{{ t('备份包含库 ：') }}</div>
            <div class="content-value">
              <BackupDbTags :list="data.restore_backup_file.backup_db_list" />
            </div>
            <div class="content-label">{{ t('备份排除库 ：') }}</div>
            <div class="content-value">
              <BackupDbTags
                :list="data.restore_backup_file.excluded_db_list"
                theme="warning" />
            </div>
            <div class="content-label">{{ t('数据库大小 ：') }}</div>
            <div class="content-value">{{ bytePretty((data.restore_backup_file.backup_db_size_kb ?? 0) * 1024) }}</div>
            <div class="content-label">{{ t('备份文件大小 ：') }}</div>
            <div class="content-value">
              {{ bytePretty((data.restore_backup_file.backup_file_size_kb ?? 0) * 1024) }}
            </div>
            <div
              v-if="data.restore_backup_file.bill_id"
              class="content-label">
              {{ t('关联单据 ：') }}
            </div>
            <div
              v-if="data.restore_backup_file.bill_id"
              class="content-value">
              <RouterLink
                target="_blank"
                :to="{
                  name: 'ticketDetail',
                  params: { ticketId: data.restore_backup_file.bill_id },
                }">
                {{ data.restore_backup_file.bill_id }}
              </RouterLink>
            </div>
          </div>
        </template>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_list"
      :title="t('恢复库')"
      :width="200">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.db_list" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_db_list"
      :title="t('排除库')"
      :width="200">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.ignore_db_list" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_db_name"
      :title="t('恢复后库名')"
      :width="300">
      <template #default="{ row: data }: { row: RowData }">
        <span v-if="!data.rename_infos.length"> -- </span>
        <div
          v-else
          class="rename-block">
          <template
            v-for="item in data.rename_infos"
            :key="item.db_name">
            <div class="rename-item">
              <template v-if="item.target_db_name && item.target_db_name !== item.db_name">
                {{ item.db_name }} ➜ <span class="new-name">{{ item.target_db_name }}</span>
              </template>
              <template v-else>
                {{ item.db_name }}
              </template>
            </div>
          </template>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="rename_db_name"
      :title="t('已有库新名')"
      :width="200">
      <template #default="{ row: data }: { row: RowData }">
        <div class="rename-block">
          <template
            v-for="item in data.rename_infos"
            :key="item.db_name">
            <div
              v-if="item.rename_db_name"
              class="rename-item">
              {{ item.db_name }} ➜ <span class="new-name">{{ item.rename_db_name }}</span>
            </div>
          </template>
          <span v-if="!data.rename_infos.some((item) => item.rename_db_name)">--</span>
        </div>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import BackupDbTags from '@views/db-manage/sqlserver/SQLSERVER_ROLLBACK/components/BackupDbTags.vue';

  import { bytePretty, utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.Rollback>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.SQLSERVER_ROLLBACK_LOCAL,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .content-block {
    display: grid;
    grid-template-columns: 0fr 1fr;
    font-family: MicrosoftYaHei, sans-serif;
    line-height: 24px;
    padding: 8px 10px;

    .content-label {
      width: 80px;
      text-align: right;
      white-space: nowrap;
    }

    .content-value {
      width: 360px;
    }
  }

  .rename-block {
    font-family: Consolas, Monaco, monospace;
    line-height: 1.6;
    color: #313238;

    .rename-item {
      margin-bottom: 2px;
      white-space: nowrap;

      .new-name {
        color: #3a84ff;
      }
    }
  }
</style>
