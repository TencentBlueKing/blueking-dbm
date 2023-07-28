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
    <template #content="{content}">
      <template v-if="content?.todos?.length > 0">
        <div
          v-for="item in content.todos"
          :key="item.id"
          class="flow-todo">
          <div class="flow-todo__title">
            {{ item.name }}
          </div>
          <div
            v-if="item.status === 'TODO'"
            class="operations">
            <BkPopover
              v-model:is-show="state.confirmTips"
              theme="light"
              trigger="manual"
              :width="320">
              <BkButton
                class="w-88 mr-8"
                :loading="state.isLoading"
                theme="primary"
                @click="handleConfirmToggle(true)">
                {{ getConfirmText(item) }}
              </BkButton>
              <template #content>
                <div class="todos-todos-tips-content">
                  <div class="todos-tips-content__desc">
                    {{ getConfirmTips(item) }}
                  </div>
                  <div class="todos-tips-content__buttons">
                    <BkButton
                      :loading="state.isLoading"
                      size="small"
                      theme="primary"
                      @click="handleConfirm('APPROVE', item)">
                      {{ getConfirmText(item) }}
                    </BkButton>
                    <BkButton
                      :disabled="state.isLoading"
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
                :loading="state.isLoading"
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
                      :loading="state.isLoading"
                      size="small"
                      theme="danger"
                      @click="handleConfirm('TERMINATE', item)">
                      {{ $t('终止单据') }}
                    </BkButton>
                    <BkButton
                      :disabled="state.isLoading"
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
            {{ item.done_by }} 处理完成，
            操作：<span :class="String(item.status).toLowerCase()">{{ getOperation(item) }}</span>，
            耗时：{{ getCostTimeDisplay(item.cost_time) }}
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
      <template v-if="content.flow_type === 'DESCRIBE_TASK'">
        <p>
          {{ $t('执行完成_共执行') }}
          <span class="sql-count">{{ sqlFileTotal }}</span>
          {{ $t('个SQL文件_成功') }}
          <span class="sql-count success">{{ counts.success }}</span>
          {{ $t('个_待执行') }}
          <span class="sql-count warning">{{ notExecutedCount }}</span>
          {{ $t('个_失败') }}
          <span class="sql-count danger">{{ counts.fail }}</span>
          {{ $t('个') }}
          <template v-if="content.summary">
            ，耗时：{{ getCostTimeDisplay(content.cost_time) }}，
          </template>
          <BkButton
            text
            theme="primary"
            @click="handleClickDetails">
            {{ $t('查看详情') }}
          </BkButton>
        </p>
      </template>
      <template v-if="content.status !== 'RUNNING' && content.flow_type !== 'PAUSE'">
        <p v-if="content.flow_type !== 'DESCRIBE_TASK'">
          {{ content.summary }}
          <template v-if="content.summary">
            ，耗时：
            <CostTimer
              :is-timing="content.status === 'RUNNING'"
              :value="content.cost_time" />
          </template>
          <template v-if="content.url">
            ，<a
              :href="content.url"
              target="_blank">{{ $t('任务详情') }} &gt;</a>
          </template>
        </p>
        <p
          v-if="content.end_time"
          class="flow-time">
          {{ content.end_time }}
        </p>
      </template>
    </template>
  </BkTimeline>
  <BkSideslider
    :is-show="isShow"
    render-directive="if"
    :title="$t('模拟执行_日志详情')"
    :width="960"
    @closed="handleClose">
    <SqlFileComponent
      :node-id="nodeId"
      :root-id="rootId" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { processTicketTodo } from '@services/ticket';
  import type { FlowItem, FlowItemTodo } from '@services/types/ticket';

  import { useMenu } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { getCostTimeDisplay } from '@utils';

  import FlowIcon from '../../../components/FlowIcon.vue';
  import SqlFileComponent from '../../../components/mysql/SqlLogDetails.vue';
  import useLogCounts from '../../../hooks/logCounts';

  interface Emits {
    (e: 'processed'): void
  }

  const props = defineProps({
    flows: {
      type: Array as PropType<FlowItem[]>,
      default: () => [],
    },
  });
  const emits = defineEmits<Emits>();
  const { t } = useI18n();

  const { counts, fetchVersion } = useLogCounts();
  const menuStore = useMenu();
  const isShow = ref(false);
  const notExecutedCount = computed(() => {
    const count = sqlFileTotal.value - counts.success - counts.fail;
    return count >= 0 ? count : 0;
  });

  const state = reactive({
    confirmTips: false,
    cancelTips: false,
    isLoading: false,
  });

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    // color,
    icon: () => <FlowIcon data={flow} />,
  })));

  const sqlFileTotal = computed(() => props.flows[0]?.details?.ticket_data?.execute_sql_files?.length || 0);
  const rootId = computed(() => props.flows[0]?.details?.ticket_data?.root_id);
  const nodeId = computed(() => props.flows[0]?.details?.ticket_data?.semantic_node_id);

  watch([rootId, nodeId], ([rootId, nodeId]) => {
    if (rootId && nodeId) {
      fetchVersion(rootId, nodeId);
    }
  }, { immediate: true });

  const getConfirmText = (item: FlowItemTodo) => (item.type === 'RESOURCE_REPLENISH' ? t('重试') : t('确认执行'));
  const getConfirmTips = (item: FlowItemTodo) => (item.type === 'RESOURCE_REPLENISH' ? t('是否确认重试') : t('是否确认继续执行单据'));

  function handleClickDetails() {
    isShow.value = true;
  }

  function handleClose() {
    isShow.value = false;
  }

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
    state.isLoading = true;
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
        state.isLoading = false;
      });
  }
</script>

<style lang="less" scoped>
:deep(.bk-modal-content) {
  height: 100%;
  padding: 15px;
}

.sql-count {
  font-weight: 700;

  &.success {
    color: @success-color;
  }

  &.warning {
    color: @warning-color;
  }

  &.danger {
    color: @danger-color;
  }
}
</style>
