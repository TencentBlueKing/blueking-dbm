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
  <template
    v-if="
      content.todos.length > 0 &&
      content.flow_type === 'INNER_FLOW' &&
      content.status === 'RUNNING' &&
      content.todos.some((todoItem) => todoItem.type === 'RESOURCE_REPLENISH')
    ">
    <ManualConfirm
      v-for="item in content.todos"
      :key="item.id"
      :content="content"
      :data="item"
      @processed="handleEmitFetchData" />
  </template>
  <template
    v-else-if="
      content.todos.length > 0 &&
      ['TERMINATED', 'SUCCEEDED'].includes(content.status) &&
      isTodos === false &&
      !(content.flow_type === 'INNER_FLOW' && content.todos.every((todoItem) => todoItem.type !== 'RESOURCE_REPLENISH'))
    ">
    <FlowContentTodo
      v-for="item of content.todos"
      :key="item.id"
      :content="content"
      :data="item"
      href-target="_blank" />
  </template>
  <template v-else-if="isPause && isTodos === false">
    <div
      v-for="(todosItem, index) in content.todos"
      :key="index">
      <span>{{ t('处理人') }}: </span>
      <span>{{ todosItem.operators.join(',') }}</span>
      <template v-if="content.summary">
        ，{{ t('耗时') }}：
        <CostTimer
          :is-timing="content.status === 'RUNNING'"
          :start-time="utcTimeToSeconds(content.start_time)"
          :value="content.cost_time" />
      </template>
      <div
        v-if="todosItem.operators.includes(username)"
        class="mt-8">
        <BkPopConfirm
          :content="t('继续执行单据后无法撤回，请谨慎操作！')"
          :title="t('是否确认继续执行单据')"
          trigger="click"
          :width="320"
          @confirm="handleProcessTicket('APPROVE', todosItem)">
          <BkButton
            class="w-88 mr-8"
            theme="primary">
            {{ t('确认执行') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          :content="t('终止单据后无法撤回，请谨慎操作！')"
          :title="t('是否确认终止单据')"
          trigger="click"
          :width="320"
          @confirm="handleProcessTicket('TERMINATE', todosItem)">
          <BkButton
            class="w-88 mr-8"
            theme="danger">
            {{ t('终止单据') }}
          </BkButton>
        </BkPopConfirm>
      </div>
    </div>
  </template>
  <template v-if="content.flow_type !== 'PAUSE'">
    <div style="padding-top: 8px">
      <template
        v-if="
          content.status === 'RUNNING' &&
          (content.flow_type === 'RESOURCE_APPLY' || content.flow_type === 'RESOURCE_BATCH_APPLY')
        ">
        <DbIcon
          class="resource-apply-exclamation-fill"
          type="exclamation-fill" />
        <I18nT
          keypath="主机资源不足_等待管理员users补货_补货完成后可以前往place重试"
          tag="span">
          <template #users>
            {{ (content.todos[0]?.context?.administrators ?? []).join(';') }}
          </template>
          <template #place>
            <RouterLink
              :to="{
                name: 'MyTodos',
                query: {
                  id: content.ticket,
                },
              }">
              {{ t('我的待办') }}
            </RouterLink>
          </template>
        </I18nT>
      </template>
      <template v-else-if="content.flow_type === 'INNER_FLOW'">
        <template
          v-if="
            content.status === 'RUNNING' &&
            content.todos.length > 0 &&
            content.todos.some((todoItem) => todoItem.status === 'TODO' && todoItem.type !== 'RESOURCE_REPLENISH')
          ">
          <span>{{ t('任务') }}</span
          >“
          <span style="color: #ff9c01">{{ t('待确认') }}</span>
          ”
        </template>
        <template v-else-if="getStatusInfo(content.status)">
          <span>{{ t('任务') }}</span
          >“
          <span
            :style="{
              color: getStatusInfo(content.status)?.color || '#63656e',
            }">
            {{ getStatusInfo(content.status)?.text || content.summary }}
          </span>
          ”
        </template>
        <span v-if="content.err_msg"> ，{{ content.summary }} </span>
      </template>
      <template v-else-if="isPause && isTodos === false">
        <span>{{ t('处理人') }}: </span>
        <span>{{ _.uniq(_.flatten(content.todos.map((item) => item.operators))).join(',') }}</span>
      </template>
      <template v-else>
        <span
          :style="{
            color: content.status === 'TERMINATED' ? '#ea3636' : '#63656e',
          }">
          {{ content.summary }}
        </span>
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
      <slot name="extra-text" />
      <template v-if="content.url">
        ，
        <a
          :href="content.url"
          target="_blank">
          {{ t('查看详情') }} &gt;
        </a>
      </template>
    </div>
    <div>
      <BkPopConfirm
        v-if="
          content.err_code === 2 ||
          (content.flow_type === 'INNER_FLOW' && content.status === 'FAILED' && content.err_msg)
        "
        :content="t('重新执行后无法撤回，请谨慎操作！')"
        :title="t('是否确认重试此步骤')"
        trigger="click"
        :width="320"
        @confirm="handleConfirmRetry(content)">
        <BkButton
          class="w-88 mt-8"
          :disabled="btnState.retryLoading || btnState.terminateLoading"
          :loading="btnState.retryLoading"
          theme="primary">
          {{ t('重试') }}
        </BkButton>
      </BkPopConfirm>
      <BkPopConfirm
        v-if="content.flow_type === 'INNER_FLOW' && content.status === 'FAILED' && content.err_msg"
        :content="t('终止执行后无法撤回，请谨慎操作！')"
        :title="t('是否确认终止执行单据')"
        trigger="click"
        :width="320"
        @confirm="handleConfirmTerminal(content)">
        <BkButton
          class="w-88 ml-8 mt-8"
          :disabled="btnState.terminateLoading || btnState.retryLoading"
          :loading="btnState.terminateLoading"
          theme="danger">
          {{ t('终止') }}
        </BkButton>
      </BkPopConfirm>
    </div>
    <div
      v-if="content.end_time"
      class="flow-time">
      {{ utcDisplayTime(content.end_time) }}
    </div>
  </template>
  <!-- 系统自动终止 -->
  <template v-if="content.err_code === 3 && content.context.expire_time && content.todos.length === 0">
    <div style="margin-top: 8px; color: #ea3636">
      <span>{{ t('system已处理') }}</span>
      <span> ({{ t('超过n天未处理，自动终止', { n: content.context.expire_time }) }}) </span>
    </div>
    <div class="flow-time">
      {{ utcDisplayTime(content.update_at) }}
    </div>
  </template>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { processTicketTodo, retryTicketFlow, revokeTicketFlow } from '@services/source/ticket';
  import type { FlowItem } from '@services/types/ticket';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ManualConfirm from '@views/tickets/my-todos/components/details/components/flow/components/approve/ManualConfirm.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import FlowContentTodo from './components/ContentTodo.vue';

  interface Emits {
    (e: 'fetch-data'): void;
  }

  interface Props {
    ticketData: TicketModel<unknown>;
    content: FlowItem;
    isTodos?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    isTodos: false,
    flows: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { username } = useUserProfile();

  const btnState = reactive({
    terminateLoading: false,
    retryLoading: false,
  });

  const isPause = computed(() => {
    const { content } = props;
    return content.status === 'RUNNING' && content.flow_type === 'PAUSE';
  });

  // const displayExpiredTime = computed(() => {
  //   const expireTime = props.content.context.expire_time;
  //   if (!expireTime) {
  //     return '';
  //   }

  //   if (expireTime * 24 > 72) {
  //     return `${expireTime} ${t('天')}`;
  //   }

  //   return `${expireTime * 24} ${t('小时')}`;
  // });

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
      RUNNING: {
        text: t('执行中'),
        color: '#3a84ff',
      },
      TERMINATED: {
        text: t('已终止'),
        color: '#ea3636',
      },
    };
    return infoMap[status] ? infoMap[status] : null;
  };

  const handleConfirmTerminal = (item: FlowItem) => {
    btnState.terminateLoading = true;
    revokeTicketFlow({
      ticketId: item.ticket,
      flow_id: item.id,
    })
      .then(() => {
        emits('fetch-data');
      })
      .finally(() => {
        btnState.terminateLoading = false;
      });
  };

  const handleConfirmRetry = (item: FlowItem) => {
    btnState.retryLoading = true;
    retryTicketFlow({
      ticketId: item.ticket,
      flow_id: item.id,
    })
      .then(() => {
        emits('fetch-data');
      })
      .finally(() => {
        btnState.retryLoading = false;
      });
  };

  const handleProcessTicket = (action: 'APPROVE' | 'TERMINATE', todoItem: FlowItem['todos'][number]) =>
    processTicketTodo({
      action,
      todo_id: todoItem.id,
      ticket_id: props.content.ticket,
      params: {},
    }).then(() => {
      emits('fetch-data');
    });

  const handleEmitFetchData = () => {
    emits('fetch-data');
  };
</script>

<style lang="less" scoped>
  .resource-apply-exclamation-fill {
    margin-right: 4px;
    font-size: 14px;
    color: #ff9c01;
  }
</style>

<style lang="less">
  .todos-tips-content {
    .todos-tips-content__desc {
      padding: 8px 0 24px;
      font-size: @font-size-mini;
      color: @title-color;
    }

    .todos-tips-content__buttons {
      text-align: right;

      .bk-button {
        min-width: 62px;
        margin-left: 8px;
        font-size: @font-size-mini;
      }
    }
  }
</style>
