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
  <PrimaryTable
    :columns="columns"
    :data="tableData"
    row-key="ip" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterCutoff>;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_CUTOFF,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    { colKey: 'ip', ellipsis: true, title: t('待替换的主机') },
    { colKey: 'role', ellipsis: true, title: t('角色类型') },
    { colKey: 'cluster_domain', ellipsis: true, title: t('所属集群') },
    { colKey: 'spec_name', ellipsis: true, title: t('规格需求') },
  ];

  const tableData = computed(
    () => props.ticketDetails.details.infos?.flatMap((info) => info.display_info?.data ?? []) ?? [],
  );
</script>
