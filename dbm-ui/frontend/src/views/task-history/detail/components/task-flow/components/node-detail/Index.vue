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
  <BkSideslider
    v-model:is-show="isShow"
    class="node-log-main"
    quick-close
    render-directive="if"
    :width="960"
    @hidden="handleClose">
    <template #header>
      <div class="log-header">
        <div class="log-header-left">
          <span class="main-title">{{ t('节点详情') }}</span>
          <span
            v-overflow-tips="{
              content: nodeData.name,
              theme: 'light',
            }"
            class="node-name text-overflow">
            {{ nodeData.name }}
          </span>
          <div class="log-header-info">
            <BkTag
              class="ml-5 mr-5"
              :theme="statusInfo.theme">
              {{ statusInfo.text }}
            </BkTag>
            <div
              v-if="STATUS_FAILED && nodeData.retry > 0"
              class="retry-display">
              <span class="display-text">{{ t('重试') }}</span>
              <span class="display-count">{{ nodeData.retry }}</span>
            </div>
            <BkTag
              v-if="nodeData.skip"
              class="ml-4 mr-4"
              style="background: #7cb560"
              theme="success"
              type="filled">
              {{ t('已跳过') }}
            </BkTag>
            <BkTag>
              {{ t('耗时') }}
              <span class="mr-4">:</span>
              <CostTimer
                :is-timing="STATUS_RUNNING"
                :start-time="nodeData.started_at"
                :value="costTime" />
            </BkTag>
          </div>
        </div>
        <template v-if="STATUS_FAILED">
          <BkPopConfirm
            v-if="nodeData.retryable"
            :confirm-text="t('确认继续')"
            :content="t('将会重新执行')"
            :title="t('确认重试当前节点？')"
            trigger="click"
            width="288"
            @confirm="handleRetry">
            <BkButton
              class="mr-8"
              :loading="retryLoading">
              <DbIcon
                class="mr-5"
                type="refresh" />{{ t('重试') }}
            </BkButton>
          </BkPopConfirm>
          <BkPopConfirm
            v-if="nodeData.skippable"
            :confirm-text="t('跳过节点')"
            :content="t('将会忽略当前节点，继续往下执行')"
            :title="t('确认跳过当前节点继续执行？')"
            trigger="click"
            width="288"
            @confirm="handleSkip">
            <BkButton :loading="skipLoading">
              <DbIcon
                class="mr-5"
                type="tiaoguo" />{{ t('跳过') }}
            </BkButton>
          </BkPopConfirm>
        </template>
        <template v-else>
          <BkPopConfirm
            v-if="STATUS_TODO"
            :confirm-text="t('继续执行')"
            :content="t('将会立即执行该节点')"
            :title="t('确认继续执行？')"
            trigger="click"
            width="288"
            @confirm="handleTodo">
            <BkButton
              class="mr-8"
              :loading="todoLoading">
              <DbIcon
                class="mr-5"
                type="dengdaiqueren" />{{ t('确认继续') }}
            </BkButton>
          </BkPopConfirm>
          <BkPopConfirm
            v-if="STATUS_RUNNING"
            :confirm-config="{
              theme: 'danger',
            }"
            :confirm-text="t('强制失败')"
            :content="t('将会终止节点运行，并置为强制失败状态')"
            :title="t('确认强制失败？')"
            trigger="click"
            width="288"
            @confirm="handleForceFail">
            <BkButton :loading="forceFailLoading">
              <DbIcon
                class="mr-5"
                type="qiangzhizhongzhi" />{{ t('强制失败') }}
            </BkButton>
          </BkPopConfirm>
        </template>
        <!-- <template v-if="failedNodes.length > 0">
          <BkButton
            v-bk-tooltips="t('上一个失败节点')"
            class="quick-btn"
            :disabled="currentFailNodeLogIndex === 0"
            @click="() => handleClickQuickGoto(false)">
            <DbIcon type="up-big" />
          </BkButton>
          <BkButton
            v-bk-tooltips="t('下一个失败节点')"
            class="quick-btn ml-8 mr-16"
            :disabled="currentFailNodeLogIndex === failedNodes.length - 1"
            @click="() => handleClickQuickGoto(true)">
            <DbIcon type="down-big" />
          </BkButton>
        </template> -->
      </div>
    </template>
    <template #default>
      <BkTab
        v-model:active="activePanelId"
        class="node-detail-tab-main"
        type="card-grid">
        <BkTabPanel
          :label="t('执行日志')"
          name="log">
          <ExecuteLog
            :is-show="isShow"
            :node="node"
            :root-id="rootId" />
        </BkTabPanel>
        <BkTabPanel
          :label="t('输入输出')"
          name="i/o">
          <InputOutput
            :node-id="nodeData.id"
            :root-id="rootId" />
        </BkTabPanel>
        <BkTabPanel
          :label="t('操作记录')"
          name="record">
          <OperationRecord
            :node-id="nodeData.id"
            :root-id="rootId" />
        </BkTabPanel>
      </BkTab>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { forceFailflowNode, retryTaskflowNode, skipTaskflowNode } from '@services/source/taskflow';
  import { ticketBatchProcessTodo } from '@services/source/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import DbLog from '@components/db-log/index.vue';

  import { messageSuccess } from '@utils';

  import { type Node } from '../flow-canvas/utils';

  import ExecuteLog from './components/execute-log/Index.vue';
  import InputOutput from './components/input-output/Index.vue';
  import OperationRecord from './components/OperationRecord.vue';

  interface Props {
    node?: Node;
    rootId: string;
  }

  interface Emits {
    (e: 'close'): void;
    (e: 'refresh'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    node: () => ({}) as Node,
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const NODE_STATUS_TEXT: Record<string, string> = {
    CREATED: t('待执行'),
    FAILED: t('执行失败'),
    FINISHED: t('执行成功'),
    READY: t('待执行'),
    REVOKED: t('已终止'),
    RUNNING: t('执行中'),
    SKIPPED: t('跳过'),
  };

  const dbLogRef = ref<InstanceType<typeof DbLog>>();
  const activePanelId = ref('log');
  const todoLoading = ref(false);

  const nodeData = computed(() => props.node || {});
  const STATUS_RUNNING = computed(() => nodeData.value.status === 'RUNNING');
  const STATUS_FAILED = computed(() => nodeData.value.status === 'FAILED');
  const STATUS_TODO = computed(() => !!nodeData.value.todoId);
  const statusInfo = computed(() => {
    const status = nodeData.value.status;
    if (STATUS_TODO.value && status !== 'FAILED') {
      return {
        text: t('待继续'),
        theme: 'warning',
      };
    }
    const themesMap = {
      CREATED: 'default',
      FAILED: 'danger',
      FINISHED: 'success',
      RUNNING: 'info',
    };

    return {
      text: NODE_STATUS_TEXT[status],
      theme: themesMap[status as keyof typeof themesMap] || 'default',
    };
  });
  const costTime = computed(() => {
    const { started_at: startedAt, updated_at: updatedAt } = nodeData.value;
    if (startedAt && updatedAt) {
      const time = updatedAt - startedAt;
      return time <= 0 ? 0 : time;
    }
    return 0;
  });

  const { loading: retryLoading, run: runRetryTaskflowNode } = useRequest(retryTaskflowNode, {
    manual: true,
    onSuccess: () => {
      handleOperateSuccess();
    },
  });

  const { loading: skipLoading, run: runSkipTaskflowNode } = useRequest(skipTaskflowNode, {
    manual: true,
    onSuccess: () => {
      handleOperateSuccess();
    },
  });

  const { loading: forceFailLoading, run: runForceFailTaskflowNode } = useRequest(forceFailflowNode, {
    manual: true,
    onSuccess: () => {
      handleOperateSuccess();
    },
  });

  const handleOperateSuccess = () => {
    messageSuccess(t('操作成功'));
    emits('refresh');
  };

  const handleSkip = () => {
    runSkipTaskflowNode({
      node_id: props.node.id,
      root_id: props.rootId,
    });
  };

  const handleRetry = () => {
    runRetryTaskflowNode({
      node_id: props.node.id,
      root_id: props.rootId,
    });
  };

  const handleForceFail = () => {
    runForceFailTaskflowNode({
      node_id: props.node.id,
      root_id: props.rootId,
    });
  };

  const handleTodo = async () => {
    try {
      todoLoading.value = true;
      await ticketBatchProcessTodo({
        action: 'APPROVE',
        operations: [
          {
            params: {},
            todo_id: props.node.todoId,
          },
        ],
      });
      handleOperateSuccess();
    } finally {
      todoLoading.value = false;
    }
  };

  const handleClose = () => {
    dbLogRef.value?.destroy();
    emits('close');
    activePanelId.value = 'log';
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .tips-content {
    font-weight: normal;
    line-height: normal;

    .title {
      padding-bottom: 16px;
      text-align: left;
    }

    .btn {
      margin-top: 0;
    }
  }

  .node-log-main {
    .log-header {
      width: 100%;
      padding-right: 16px;
      .flex-center();

      .log-header-left {
        flex: 1;
        width: 0;
        padding-right: 8px;
        .flex-center();

        .main-title {
          font-size: 16px;
          color: #313238;
        }

        .node-name {
          margin-left: 10px;
          font-size: 14px;
          color: #979ba5;

          &::before {
            margin-right: 8px;
            font-size: 14px;
            color: #dcdee5;
            content: '|';
          }
        }
      }

      .log-header-info {
        padding-left: 4px;
        font-size: @font-size-normal;
        font-weight: normal;
        flex-shrink: 0;
        .flex-center();

        .retry-display {
          display: flex;
          height: 22px;
          line-height: 22px;
          text-align: center;
          border-radius: 2px;

          .display-text {
            width: 36px;
            height: 22px;
            font-size: 12px;
            font-weight: 400;
            color: #fff;
            background: #979ba5;
          }

          .display-count {
            width: 17px;
            height: 22px;
            font-size: 12px;
            font-weight: 400;
            color: #63656e;
            background: #dcdee5;
          }
        }
      }

      .log-header-btn {
        text-align: right;
        flex-shrink: 0;

        :deep(.bk-button-text) {
          font-size: 14px;
          color: @default-color;

          i {
            display: inline-block;
            margin-right: 5px;
          }
        }
      }

      .quick-btn {
        width: 32px;
        height: 32px;
      }
    }

    :deep(.bk-sideslider-content) {
      height: calc(100vh - 100px);
      padding: 16px;
      background: #f5f7fa;
    }
  }

  .node-detail-tab-main {
    height: 100%;

    :deep(.bk-tab-content) {
      height: 100%;
    }
  }
</style>
