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
  <div>
    {{ t('任务待确认') }}
    <template v-if="content.summary">
      ，{{ t('耗时') }}：
      <CostTimer
        :is-timing="content.status === 'RUNNING'"
        :start-time="utcTimeToSeconds(content.start_time)"
        :value="content.cost_time" />
    </template>
    <template v-if="content.url">
      ，
      <a
        :href="content.url"
        target="_blank">
        {{ t('查看详情') }} &gt;
      </a>
    </template>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { FlowItem } from '@services/types/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  interface Props {
    content: FlowItem;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
