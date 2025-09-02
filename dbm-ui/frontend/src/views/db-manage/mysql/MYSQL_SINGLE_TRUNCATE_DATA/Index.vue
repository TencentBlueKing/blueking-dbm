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
  <TruncateData ref="truncateRef" />
</template>

<script setup lang="ts">
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TruncateData from '@views/db-manage/mysql/MYSQL_HA_TRUNCATE_DATA/truncate-data/Index.vue';

  const truncateRef = ref();

  useTicketDetail<Mysql.TruncateData>(TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA, {
    onSuccess(ticketDetail) {
      truncateRef.value.cloneTicket(ticketDetail);
    },
  });
</script>
