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
    <InfoItem :label="t('回档类型')">
      {{ t('构造回档') }}
    </InfoItem>
    <InfoItem :label="t('回档方式')">
      {{ ticketDetails.details.infos[0]?.rollback_time ? t('指定时间回档') : t('指定备份记录回档') }}
    </InfoItem>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.infos[0].backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <InfoTableColumn
      col-key="cluster_id"
      fixed="left"
      :get-copy-value="(item: RowData) => ticketDetails.details.clusters[item.cluster_id].immute_domain"
      :min-width="300"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      v-if="ticketDetails.details.infos[0]?.rollback_time"
      col-key="rollback_time"
      :min-width="300"
      :title="t('指定时间')">
      <template #default="{ row }: { row: RowData }">
        {{ utcDisplayTime(row.rollback_time) }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="backupinfo"
      :min-width="370"
      :title="t('备份记录')">
      <template #default="{ row }: { row: RowData }">
        <div class="content-block">
          <div class="content-label">{{ t('备份记录 ：') }}</div>
          <div class="content-value">
            {{ `${row.backupinfo.mysql_role} ${utcDisplayTime(row.backupinfo.backup_time)}` }}
          </div>
          <div class="content-label">{{ t('备份 ID ：') }}</div>
          <div class="content-value">
            {{ row.backupinfo.backup_id || '--' }}
          </div>
          <div class="content-label">{{ t('备份类型 ：') }}</div>
          <div class="content-value">
            <BkTag
              v-if="backupTypeMap[row.backupinfo.backup_type]"
              :theme="backupTypeMap[row.backupinfo.backup_type].theme">
              {{ backupTypeMap[row.backupinfo.backup_type].label }}
            </BkTag>
            <span v-else>--</span>
          </div>
          <div class="content-label">{{ t('备份范围 ：') }}</div>
          <div class="content-value">
            <span
              :class="{
                [`backup-method-sign-${row.backupinfo.backup_method}`]: backupMethodMap[row.backupinfo.backup_method],
              }">
              {{ backupMethodMap[row.backupinfo.backup_method] || '--' }}
            </span>
          </div>
          <div class="content-label">{{ t('文件大小 ：') }}</div>
          <div class="content-value">{{ bytePretty(row.backupinfo?.total_filesize ?? 0) }}</div>
          <div
            v-if="row.backupinfo.bill_id"
            class="content-label">
            {{ t('关联单据 ：') }}
          </div>
          <div
            v-if="row.backupinfo.bill_id"
            class="content-value">
            <RouterLink
              v-if="row.backupinfo.bill_id"
              target="_blank"
              :to="{
                name: 'ticketDetail',
                params: {
                  ticketId: row.backupinfo.bill_id,
                },
              }">
              {{ row.backupinfo.bill_id }}
            </RouterLink>
            <span v-else>--</span>
          </div>
        </div>
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="databases"
      :min-width="120"
      :title="t('源 DB')">
      <template #default="{ row }: { row: RowData }">
        <BkTag
          v-for="item in row.databases"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="row.databases.length < 1">--</span>
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="tables"
      :min-width="120"
      :title="t('源表')">
      <template #default="{ row }: { row: RowData }">
        <BkTag
          v-for="item in row.tables"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="row.tables.length < 1">--</span>
      </template>
    </InfoTableColumn>
  </InfoTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { bytePretty, utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import InfoTable, { InfoTableColumn } from '../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.RollbackCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_ROLLBACK,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const backupMethodMap = {
    full_by_regular: t('全库备份（例行）'),
    full_by_ticket: t('全库备份（单据）'),
    non_full_by_regular: t('非全库备份（例行）'), // 过滤掉，不展示
    partial_by_ticket: t('库表备份（单据）'),
  } as Record<string, string>;

  const backupTypeMap = {
    logical: {
      label: t('逻辑备份'),
      theme: 'info',
    },
    physical: {
      label: t('物理备份'),
      theme: 'warning',
    },
  } as Record<
    string,
    {
      label: string;
      theme: 'info' | 'warning';
    }
  >;
</script>
<style lang="less" scoped>
  .content-block {
    display: grid;
    grid-template-columns: 0fr 1fr;
    font-family: MicrosoftYaHei, sans-serif;
    line-height: 24px;

    .content-label {
      width: 80px;
      text-align: right;
    }

    .content-value {
      width: 240px;
    }

    // 全库备份（例行）
    .backup-method-sign-full_by_regular::before {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      background-color: #3a84ff;
      content: '';
    }
    // 全库备份（单据）
    .backup-method-sign-full_by_ticket::before {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      background-color: #2caf5e;
      content: '';
    }
    //库表备份（单据）
    .backup-method-sign-partial_by_ticket::before {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      background-color: #f59500;
      content: '';
    }
  }
</style>
