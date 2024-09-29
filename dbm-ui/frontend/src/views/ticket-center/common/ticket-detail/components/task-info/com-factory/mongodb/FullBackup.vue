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
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('备份保存时间') }}：</span>
      <span class="ticket-details-item-value">{{ fileTagText }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('是否备份 Oplog') }}：</span>
      <span class="ticket-details-item-value">{{ oplogType }}</span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.FullBackup>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_FULL_BACKUP,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const { clusters, file_tag: fileTag, oplog, infos } = props.ticketDetails.details;

  const fileTagMap: Record<string, string> = {
    normal_backup: t('25天'),
    half_year_backup: t('6 个月'),
    a_year_backup: t('1 年'),
    forever_backup: t('3 年'),
  };

  // eslint-disable-next-line camelcase
  const fileTagText = fileTagMap[fileTag];
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

  const dataList = infos.map((item) => ({
    immute_domain: clusters[item.cluster_id].immute_domain,
    cluster_type_name: clusters[item.cluster_id].cluster_type_name,
  }));
</script>
