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
  <FlowContentInnerFlow
    v-if="content?.todos?.length > 0 && content.flow_type === 'INNER_FLOW' && isTodos === false"
    :content="content"
    @fetch-data="handleEmitFetchData" />
  <template v-else-if="content?.todos?.length > 0 && content.status === 'SUCCEEDED' && isTodos === false">
    <FlowContentTodo
      v-for="item of content.todos"
      :key="item.id"
      :data="item"
      :href-target="getHrefTarget(content)" />
  </template>
  <template v-else>
    <p>
      <template
        v-if="content.status === 'RUNNING' &&
          (content.flow_type === 'RESOURCE_APPLY' || content.flow_type === 'RESOURCE_BATCH_APPLY')">
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
            <a
              href="javascript:"
              @click="handleGoTodos">
              {{ $t('我的待办') }}
            </a>
          </template>
        </I18nT>
      </template>
      <template v-else-if="isPause && isTodos === false">
        {{ $t('请在') }} "
        <a
          href="javascript:"
          @click="handleGoTodos">
          {{ $t('我的待办') }}
        </a>
        " {{ $t('中确认') }}
      </template>
      <template v-else>
        {{ content.summary }}
      </template>
      <template v-if="content.summary">
        ，{{ $t('耗时') }}：
        <CostTimer
          :is-timing="content.status === 'RUNNING'"
          :value="content.cost_time" />
      </template>
      <template v-if="content.url">
        ，<a
          :href="content.url"
          :target="getHrefTarget(content)">{{ $t('查看详情') }} &gt;</a>
      </template>
      <slot name="extra-text" />
    </p>
    <p
      v-if="content.end_time"
      class="flow-time">
      {{ content.end_time }}
    </p>
    <BkPopover
      v-if="content.err_code === 2"
      v-model:is-show="state.confirmTips"
      theme="light"
      trigger="manual"
      :width="320">
      <BkButton
        ref="retryButtonRef"
        class="w-88 mt-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleConfirmToggle">
        {{ $t('重试') }}
      </BkButton>
      <template #content>
        <div
          v-clickoutside:[retryButtonRef?.$el]="handleConfirmCancel"
          class="ticket-flow-content">
          <div class="ticket-flow-content-desc">
            {{ $t('是否确认重新执行单据') }}
          </div>
          <div class="ticket-flow-content-buttons">
            <BkButton
              :loading="state.isLoading"
              size="small"
              theme="primary"
              @click="handleConfirm(content)">
              {{ $t('确认') }}
            </BkButton>
            <BkButton
              :disabled="state.isLoading"
              size="small"
              @click="handleConfirmCancel">
              {{ $t('取消') }}
            </BkButton>
          </div>
        </div>
      </template>
    </BkPopover>
  </template>
</template>

<script setup lang="ts">
  import { retryTicketFlow } from '@services/source/ticket';
  import type { FlowItem } from '@services/types/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import FlowContentInnerFlow from './components/ContentInnerFlow.vue';
  import FlowContentTodo from './components/ContentTodo.vue';

  interface Emits {
    (e: 'fetch-data'): void
  }

  interface Props {
    content: FlowItem,
    isTodos?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    isTodos: false,
  });
  const emits = defineEmits<Emits>();

  const router = useRouter();

  const retryButtonRef = ref();
  const state = reactive({
    confirmTips: false,
    isLoading: false,
  });
  const isPause = computed(() => {
    const { content } = props;
    return content.status === 'RUNNING' && content.flow_type === 'PAUSE';
  });

  function getHrefTarget(content: FlowItem) {
    return content.flow_type === 'BK_ITSM' ? '_blank' : '_self';
  }

  function handleGoTodos() {
    router.push({
      name: 'MyTodos',
      query: {
        filterId: props.content.ticket,
      },
    });
  }

  function handleConfirmToggle() {
    state.confirmTips = !state.confirmTips;
  }

  function handleConfirmCancel() {
    state.confirmTips = false;
  }

  function handleConfirm(item: FlowItem) {
    state.confirmTips = false;
    state.isLoading = true;
    retryTicketFlow({
      ticketId: item.ticket,
      flow_id: item.id,
    })
      .then(() => {
        emits('fetch-data');
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleEmitFetchData() {
    emits('fetch-data');
  }
</script>

<style scoped>
.resource-apply-exclamation-fill {
  margin-right: 4px;
  font-size: 14px;
  color: #ff9c01;
}
</style>
