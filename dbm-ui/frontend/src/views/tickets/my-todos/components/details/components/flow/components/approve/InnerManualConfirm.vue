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
    <template v-if="content.status === 'RUNNING'">
      {{ t('任务') }}“
      <span
        v-if="isTodo"
        style="color: #ff9c01">
        {{ t('待确认') }}
      </span>
      <span
        v-else
        style="color: #3a84ff">
        {{ t('执行中') }}
      </span>
      ”
    </template>
    <template v-else>
      <span v-if="getStatusInfo(content.status)"> {{ t('任务') }}“ </span>
      <span
        :style="{
          color: getStatusInfo(content.status)?.color || 'inhert',
        }">
        {{ getStatusInfo(content.status)?.text || content.summary }}
      </span>
      ”
      <template v-if="content.err_msg">
        <span>，{{ t('处理人') }}: </span>
        <span>{{ ticketData.updater }}</span>
      </template>
    </template>
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
  <div
    v-if="content.end_time"
    class="flow-time">
    {{ utcDisplayTime(content.end_time) }}
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import type { FlowItem } from '@services/types/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    content: FlowItem;
    ticketData: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isTodo = computed(() => props.content.todos.some((todoItem) => todoItem.status === 'TODO'));

  const getStatusInfo = (status: string) => {
    const infoMap: Record<
      string,
      {
        text: string;
        color: string;
      }
    > = {
      SUCCEEDED: {
        text: t('执行成功'),
        color: '#14a568',
      },
      FAILED: {
        text: t('执行失败'),
        color: '#ea3636',
      },
      TERMINATED: {
        text: t('已终止'),
        color: '#ea3636',
      },
    };
    return infoMap[status] ? infoMap[status] : null;
  };
</script>
