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
      {{ rollbackTypeLabel[ticketDetails.details.rollback_cluster_type] }}
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
      :min-width="180">
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
      :min-width="300">
      <template #default="{ data }: { data: RowData }">
        <div class="content-block">
          <div class="content-label">{{ t('备份文件名：') }}</div>
          <div class="content-value">
            {{ `${data.backupinfo.mysql_role} ${utcDisplayTime(data.backupinfo.backup_time)}` }}
          </div>
          <div class="content-label">{{ t('备份范围：') }}</div>
          <div class="content-value">{{ data.backupinfo.is_full_backup === '1' ? t('全库备份') : t('库表备份') }}</div>
          <div class="content-label">{{ t('备份类型：') }}</div>
          <div class="content-value">
            {{ data.backupinfo.backup_type === 'logical' ? t('逻辑备份') : t('物理备份') }}
          </div>
          <div class="content-label">{{ t('发起方式：') }}</div>
          <div class="content-value">{{ data.backupinfo.bill_id ? t('单据备份') : t('例行备份') }}</div>
          <div class="content-label">{{ t('文件大小：') }}</div>
          <div class="content-value">{{ bytePretty(data.backupinfo?.total_filesize ?? 0) }}</div>
          <div
            v-if="data.backupinfo.bill_id"
            class="content-label">
            {{ t('关联单据：') }}
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
      v-if="['BUILD_INTO_EXIST_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      :label="t('目标集群')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.target_cluster_id]?.immute_domain || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="['BUILD_INTO_NEW_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      :label="t('新集群主机')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ data.resource_spec.rollback_host.hosts?.[0]?.ip || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import { bytePretty, utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.RollbackCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_FIXPOINT,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const rollbackTypeLabel = {
    BUILD_INTO_EXIST_CLUSTER: t('在已有集群上构造数据'),
    BUILD_INTO_NEW_CLUSTER: t('在新集群上构造数据'),
  } as Record<string, string>;
</script>
<style lang="less" scoped>
  .content-block {
    display: grid;
    grid-template-columns: 0fr 1fr;

    .content-label {
      width: 80px;
      text-align: right;
    }

    .content-value {
      width: 200px;
    }
  }
</style>
