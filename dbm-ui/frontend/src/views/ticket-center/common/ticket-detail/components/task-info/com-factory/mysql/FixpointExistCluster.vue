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
    <InfoItem :label="t('构造类型')">
      {{ t('在已有集群上构造数据') }}
    </InfoItem>
    <InfoItem :label="t('构造方式')">
      {{ ticketDetails.details.infos[0]?.rollback_time ? t('指定时间构造数据') : t('指定备份记录构造数据') }}
    </InfoItem>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.infos[0].backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      fixed="left"
      :label="t('源集群')"
      :min-width="300">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="ticketDetails.details.infos[0]?.rollback_time"
      :label="t('指定时间')"
      :min-width="300">
      <template #default="{ data }: { data: RowData }">
        {{ utcDisplayTime(data.rollback_time) }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('备份记录')"
      :min-width="370">
      <template #default="{ data }: { data: RowData }">
        <div class="content-block">
          <div class="content-label">{{ t('备份记录 ：') }}</div>
          <div class="content-value">
            {{ `${data.backupinfo.mysql_role} ${utcDisplayTime(data.backupinfo.backup_time)}` }}
          </div>
          <div class="content-label">{{ t('备份 ID ：') }}</div>
          <div class="content-value">
            {{ data.backupinfo.backup_id || '--' }}
          </div>
          <div class="content-label">{{ t('备份类型 ：') }}</div>
          <div class="content-value">
            <BkTag
              v-if="backupTypeMap[data.backupinfo.backup_type]"
              :theme="backupTypeMap[data.backupinfo.backup_type].theme">
              {{ backupTypeMap[data.backupinfo.backup_type].label }}
            </BkTag>
            <span v-else>--</span>
          </div>
          <div class="content-label">{{ t('备份范围 ：') }}</div>
          <div class="content-value">
            <span
              :class="{
                [`backup-method-sign-${data.backupinfo.backup_method}`]: backupMethodMap[data.backupinfo.backup_method],
              }">
              {{ backupMethodMap[data.backupinfo.backup_method] || '--' }}
            </span>
          </div>
          <div class="content-label">{{ t('文件大小 ：') }}</div>
          <div class="content-value">{{ bytePretty(data.backupinfo?.total_filesize ?? 0) }}</div>
          <div
            v-if="data.backupinfo.bill_id"
            class="content-label">
            {{ t('关联单据 ：') }}
          </div>
          <div
            v-if="data.backupinfo.bill_id"
            class="content-value">
            <RouterLink
              v-if="data.backupinfo.bill_id"
              target="_blank"
              :to="{
                name: 'ticketDetail',
                params: {
                  ticketId: data.backupinfo.bill_id,
                },
              }">
              {{ data.backupinfo.bill_id }}
            </RouterLink>
            <span v-else>--</span>
          </div>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('源 DB')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.databases"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.databases.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('源表')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.tables"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.tables.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.target_cluster_id]?.immute_domain || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('受影响的 DB')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        <span v-if="!data.affect_db?.length">--</span>
        <BkButton
          v-else
          text
          theme="primary"
          @click="() => handleClick(data)">
          {{ data.affect_db.length }}
        </BkButton>
      </template>
    </BkTableColumn>
  </BkTable>
  <BkSideslider
    v-if="rowData"
    v-model:is-show="isShowSlider"
    :width="900">
    <template #header>
      <span>{{ t('受影响的 DB') }}</span>
      <BkTag class="ml-10">
        {{ t('源集群：') }}{{ ticketDetails.details.clusters[rowData.cluster_id].immute_domain }}
      </BkTag>
      <BkTag
        v-for="item in rowData.databases"
        :key="item"
        class="ml-4">
        {{ t('源 DB：') }}{{ item }}
      </BkTag>
      <BkTag
        v-for="item in rowData.databases"
        :key="item"
        class="ml-4">
        {{ t('源表：') }}{{ item }}
      </BkTag>
    </template>
    <div class="priview-conflict-dbs">
      <BkAlert
        class="mb-16"
        closable
        theme="warning">
        {{
          t('当前备份记录为backup_method、backup_type。注意：tip', {
            backup_method: backupMethodMap[rowData.backupinfo?.backup_method],
            backup_type: rowData.backupinfo?.backup_type === 'logical' ? t('逻辑备份') : t('物理备份'),
            tip: disabled ? t('受影响的DB在执行时将被强制清空，请谨慎操作！') : t('受影响的DB需在执行前手动清档'),
          })
        }}
      </BkAlert>
      <BkTable :data="tableData">
        <BkTableColumn
          field="dbname"
          :label="t('受影响的 DB')">
          <template #header>
            <span>{{ t('受影响的 DB') }}（{{ tableData.length }}）</span>
          </template>
          <template #default="{ row }">
            <span>{{ row.dbname }}</span>
          </template>
        </BkTableColumn>
      </BkTable>
    </div>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { bytePretty, utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.RollbackCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

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

  const isShowSlider = ref(false);
  const rowData = ref<RowData>();
  const disabled = ref(false);
  const tableData = ref<
    {
      dbname: string;
    }[]
  >([]);

  const handleClick = (data: RowData) => {
    rowData.value = data;
    tableData.value = (data.affect_db || []).map((dbname) => ({ dbname }));
    if (data.backupinfo?.backup_type === 'physical') {
      disabled.value = true;
    }
    if (props.ticketDetails.details.infos[0]?.rollback_time) {
      disabled.value = true;
    }
    isShowSlider.value = true;
  };
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

  .conflict-db-head {
    border-bottom: 1px dashed #979ba5;
  }

  .required-icon::after {
    margin-left: 4px;
    line-height: 20px;
    color: @danger-color;
    content: '*';
  }

  .priview-conflict-dbs {
    margin: 18px 24px;
  }
</style>
