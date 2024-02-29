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
  <BkTimeline :list="flowTimeline">
    <template #content="{ content }">
      <template v-if="content?.todos?.length > 0">
        <div
          v-for="item in content.todos"
          :key="item.id"
          class="flow-todo">
          <div>
            <div class="flow-todo__title">
              {{ item.name }}
            </div>
            <div
              v-if="content.err_msg"
              class="mb-8">
              {{ content.err_msg }}
            </div>
            <template v-if="isShowResourceApply(item)">
              ，
              <BkButton
                text
                theme="primary"
                @click="handleToApply">
                {{ $t('请前往补货') }}
              </BkButton>
            </template>
          </div>
          <div
            v-if="item.status === 'TODO'"
            class="operations mt-8">
            <BkPopover
              v-model:is-show="state.confirmTips"
              theme="light"
              trigger="manual"
              :width="320">
              <BkButton
                class="w-88 mr-8"
                :loading="state.isApproveLoading"
                theme="primary"
                @click="handleConfirmToggle(true)">
                {{ getConfirmText(item) }}
              </BkButton>
              <template #content>
                <div class="todos-tips-content">
                  <div class="todos-tips-content__desc">
                    {{ getConfirmTips(item) }}
                  </div>
                  <div class="todos-tips-content__buttons">
                    <BkButton
                      :loading="state.isApproveLoading"
                      size="small"
                      theme="primary"
                      @click="handleConfirm('APPROVE', item)">
                      {{ getConfirmText(item) }}
                    </BkButton>
                    <BkButton
                      :disabled="state.isApproveLoading"
                      size="small"
                      @click="handleConfirmToggle(false)">
                      {{ $t('取消') }}
                    </BkButton>
                  </div>
                </div>
              </template>
            </BkPopover>
            <BkPopover
              v-model:is-show="state.cancelTips"
              theme="light"
              trigger="manual"
              :width="320">
              <BkButton
                class="w-88 mr-8"
                :loading="state.isTerminateLoading"
                theme="danger"
                @click="handleCancelToggle(true)">
                {{ $t('终止单据') }}
              </BkButton>
              <template #content>
                <div class="todos-tips-content">
                  <div class="todos-tips-content__desc">
                    {{ $t('是否确认终止单据') }}
                  </div>
                  <div class="todos-tips-content__buttons">
                    <BkButton
                      :loading="state.isTerminateLoading"
                      size="small"
                      theme="danger"
                      @click="handleConfirm('TERMINATE', item)">
                      {{ $t('终止单据') }}
                    </BkButton>
                    <BkButton
                      :disabled="state.isTerminateLoading"
                      size="small"
                      @click="handleCancelToggle(false)">
                      {{ $t('取消') }}
                    </BkButton>
                  </div>
                </div>
              </template>
            </BkPopover>
          </div>
          <div
            v-else
            class="flow-todo__infos">
            {{ item.done_by }} {{ $t('处理完成') }}， {{ $t('操作') }}：
            <span :class="String(item.status).toLowerCase()">
              {{ getOperation(item) }}
            </span>
            ， {{ $t('耗时') }}：{{ getCostTimeDisplay(item.cost_time) }}
            <template v-if="item.url">
              ，<a :href="item.url">{{ $t('查看详情') }} &gt;</a>
            </template>
            <p
              v-if="item.done_at"
              class="flow-time">
              {{ item.done_at }}
            </p>
          </div>
        </div>
      </template>
      <template v-else>
        <FlowContent
          :content="content"
          is-todos />
      </template>
    </template>
  </BkTimeline>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { processTicketTodo } from '@services/source/ticket';
  import type {
    FlowItem,
    FlowItemTodo,
  } from '@services/types/ticket';

  import {
    useMenu,
    useUserProfile,
  } from '@stores';

  import FlowIcon from '@views/tickets/common/components/flow-content/components/FlowIcon.vue';
  import FlowContent from '@views/tickets/common/components/flow-content/Index.vue';

  import { getCostTimeDisplay } from '@utils';

  interface Props {
    flows?: FlowItem[]
  }

  interface Emits {
    (e: 'processed'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    flows: () => [],
  });
  const emits = defineEmits<Emits>();

  const { username } = useUserProfile();
  const router = useRouter();
  const { t } = useI18n();

  const menuStore = useMenu();

  const state = reactive({
    confirmTips: false,
    cancelTips: false,
    isApproveLoading: false,
    isTerminateLoading: false,
  });

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    // color,
    icon: () => <FlowIcon data={flow} />,
  })));

  const isShowResourceApply = (data: FlowItemTodo) => {
    const { administrators = [] } = data.context;
    return data.type === 'RESOURCE_REPLENISH' && data.status === 'TODO' && administrators.includes(username);
  };

  const getConfirmText = (item: FlowItemTodo) => (item.type === 'RESOURCE_REPLENISH' ? t('重试') : t('确认执行'));
  const getConfirmTips = (item: FlowItemTodo) => (item.type === 'RESOURCE_REPLENISH' ? t('是否确认重试') : t('是否确认继续执行单据'));

  function getOperation(item: FlowItemTodo) {
    const text = {
      DONE_SUCCESS: getConfirmText(item),
      DONE_FAILED: t('终止单据'),
      RUNNING: '--',
      TODO: '--',
    };
    return text[item.status];
  }

  function handleConfirmToggle(show: boolean) {
    state.confirmTips = show;
    state.cancelTips = false;
  }

  function handleCancelToggle(show: boolean) {
    state.cancelTips = show;
    state.confirmTips = false;
  }

  function handleConfirm(action: 'APPROVE' | 'TERMINATE', item: FlowItemTodo) {
    state.confirmTips = false;
    state.cancelTips = false;
    if (action === 'APPROVE') {
      state.isApproveLoading = true;
    } else {
      state.isTerminateLoading = true;
    }

    processTicketTodo({
      action,
      todo_id: item.id,
      ticket_id: item.ticket,
      params: {},
    })
      .then(() => {
        emits('processed');
        menuStore.fetchTodosCount();
      })
      .finally(() => {
        if (action === 'APPROVE') {
          state.isApproveLoading = false;
        } else {
          state.isTerminateLoading = false;
        }
      });
  }

  const handleToApply = () => {
    router.push({
      name: 'resourcePool',
    });
  };
</script>
