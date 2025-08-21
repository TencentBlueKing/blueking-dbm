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
    :data="tableData"
    ellipsis
    row-key="ip">
    <TableColumn
      col-key="ip"
      :title="t('待替换的主机')" />
    <TableColumn
      col-key="role"
      :title="t('角色类型')" />
    <TableColumn
      col-key="cluster_domain"
      :title="t('所属集群')" />
    <TableColumn
      col-key="spec_name"
      :title="t('规格需求')" />
  </PrimaryTable>
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

  const tableData = computed(() => {
    const data = props.ticketDetails.details.infos?.flatMap((info) => info.display_info?.data ?? []) ?? [];
    return data;
  });
</script>
