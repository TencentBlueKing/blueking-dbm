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
  <DbCard
    v-model:collapse="isCardCollapse"
    mode="collapse"
    :title="t('实施进度')">
    <RenderFlow :ticket-detail="data" />
  </DbCard>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import RenderFlow from './RenderFlow.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  defineOptions({
    name: 'TicketFlowInfo',
  });

  defineProps<Props>();

  const { t } = useI18n();

  const isCardCollapse = ref(true);
</script>
