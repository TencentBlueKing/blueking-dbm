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
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { RedisDBReplaceDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<RedisDBReplaceDetails>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('待替换的主机'),
      field: 'ip',
      showOverflowTooltip: true,
    },
    {
      label: t('角色类型'),
      field: 'role',
    },
    {
      label: t('所属集群'),
      field: 'cluster_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('规格需求'),
      field: 'spec_name',
      showOverflowTooltip: true,
    },
  ];

  const tableData = computed(
    () => props.ticketDetails.details.infos?.flatMap((info) => info.display_info?.data ?? []) ?? [],
  );
</script>
