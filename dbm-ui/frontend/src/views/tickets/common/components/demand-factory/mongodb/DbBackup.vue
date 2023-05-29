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
  <DbOriginalTable
    class="details-backup__table"
    :columns="columns"
    :data="dataList" />
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('备份文件保存时间') }}：</span>
        <span class="ticket-details__item-value">{{ fileTag }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('是否开启 Oplog') }}：</span>
        <span class="ticket-details__item-value">{{ oplogType }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { TicketDetails } from '@services/types/ticket';

  interface DbBackupDetails {
    clusters: {
      [clusterId: string]: {
        alias: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        cluster_type: string;
        cluster_type_name: string;
        creator: string;
        db_module_id: number;
        disaster_tolerance_level: string;
        id: number;
        immute_domain: string;
        major_version: string;
        name: string;
        phase: string;
        region: string;
        status: string;
        tag: {
          bk_biz_id?: number;
          name: string;
          type: string;
        }[];
        time_zone: string;
        updater: string;
      };
    };
    file_tag: string;
    infos: {
      cluster_id: number;
    }[];
    oplog: boolean;
  }

  interface Props {
    ticketDetails: TicketDetails<DbBackupDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    clusters,
    file_tag,
    oplog,
    infos,
  } = props.ticketDetails.details;

  // eslint-disable-next-line camelcase
  const fileTag = file_tag === 'normal_backup' ? t('常规备份（25天）') : t('长期备份（3年）');
  const oplogType = oplog ? t('是') : t('否');

  const columns = [
    {
      label: t('目标集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('集群类型'),
      field: 'cluster_type_name',
      showOverflowTooltip: true,
    },
  ];

  const dataList = infos.map(item => ({
    immute_domain: clusters[item.cluster_id].immute_domain,
    cluster_type_name: clusters[item.cluster_id].cluster_type_name,

  }));

</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
@import "@views/tickets/common/styles/ticketDetails.less";

.ticket-details {
  &__info {
    padding-left: 80px;
  }

  &__item {
    &-label {
      min-width: 0;
      text-align: left;
    }
  }
}

.details-backup {
  &__table {
    padding-left: 80px;
  }
}
</style>
