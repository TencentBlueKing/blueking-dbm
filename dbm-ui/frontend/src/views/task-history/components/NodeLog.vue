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
    render-directive="show"
    :width="960"
    @hidden="handleClose">
    <template #header>
      <div class="log-header">
        <div class="log-header-left">
          <span
            v-overflow-tips="{
              content: `【${nodeData.name}】 ${t('日志详情')}`,
              theme: 'light',
            }"
            class="log-header__title text-overflow">
            {{ `【${nodeData.name}】 ${t('日志详情')}` }}
          </span>
          <div class="log-header-info">
            <RetrySelector
              v-if="isShow"
              :node-id="nodeData.id"
              @change="handleChangeDate" />
            <BkTag
              class="ml-16 mr-16"
              :theme="status.theme">
              {{ status.text }}
            </BkTag>
            <span>
              {{ t('总耗时') }}
              <CostTimer
                :is-timing="STATUS_RUNNING"
                :start-time="nodeData.started_at"
                :value="costTime" />
            </span>
          </div>
        </div>
        <div
          v-if="STATUS_FAILED && nodeData.retryable"
          class="log-header-btn mr-8">
          <BkPopover
            v-model:is-show="refreshShow"
            theme="light"
            trigger="manual"
            :z-index="99999">
            <BkButton
              class="refresh-btn"
              :loading="retryLoading"
              @click="() => (refreshShow = true)">
              <i class="db-icon-refresh mr5" />{{ t('失败重试') }}
            </BkButton>
            <template #content>
              <div class="tips-content">
                <div class="title">
                  {{ t('确定重试吗') }}
                </div>
                <div class="btn">
                  <span
                    class="bk-button-primary bk-button mr-8"
                    @click="handleRefresh">
                    {{ t('确定') }}
                  </span>
                  <span
                    class="bk-button"
                    @click="() => (refreshShow = false)">
                    {{ t('取消') }}
                  </span>
                </div>
              </div>
            </template>
          </BkPopover>
        </div>
        <template v-if="failedNodes.length > 0">
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
        </template>
      </div>
    </template>
    <template #default>
      <div
        ref="logContentRef"
        class="log-content">
        <div class="log-tools">
          <span class="log-tools-title">
            {{ t('执行日志') }}
            <span> {{ t('日志保留30天_如需要请下载保存') }}</span>
          </span>
          <div class="log-tools-bar">
            <i
              v-bk-tooltips="t('复制')"
              class="db-icon-copy"
              @click="handleCopyLog" />
            <i
              v-bk-tooltips="t('下载')"
              class="db-icon-import"
              @click="handleDownLoaderLog" />
            <i
              v-bk-tooltips="screenIcon.text"
              :class="screenIcon.icon"
              @click="toggle" />
          </div>
        </div>
        <DbLog
          ref="dbLogRef"
          :loading="logState.loading"
          :style="{ height: isFullscreen ? 'calc(100% - 42px)' : '100%' }" />
      </div>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getNodeLog, getRetryNodeHistories, retryTaskflowNode } from '@services/source/taskflow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import DbLog from '@components/db-log/index.vue';

  import { downloadText, execCopy, messageSuccess } from '@utils';

  import { useFullscreen, useTimeoutPoll } from '@vueuse/core';

  import { NODE_STATUS_TEXT } from '../common/graphRender';
  import type { GraphNode } from '../common/utils';

  import RetrySelector from './RetrySelector.vue';

  type NodeLog = ServiceReturnType<typeof getNodeLog>[number];

  interface Props {
    failedNodes?: GraphNode[];
    node?: GraphNode;
  }

  interface Emits {
    (e: 'close'): void;
    (e: 'refresh'): void;
    (e: 'quickGoto', index: number, isNext: boolean): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    failedNodes: () => [] as NonNullable<Props['failedNodes']>,
    node: () => ({}) as NonNullable<Props['node']>,
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const getNodeLogRequest = (isInit?: boolean) => {
    if (!currentData.value.version) {
      return;
    }

    logState.loading = true;
    const params = {
      node_id: nodeData.value.id,
      root_id: rootId,
      version_id: currentData.value.version,
    };
    getNodeLog(params)
      .then((data) => {
        logState.data = data;
        dbLogRef.value!.clearLog();
        dbLogRef.value!.setLog(data);
      })
      .finally(() => {
        logState.loading = false;
        if (isInit && nodeData.value.status === 'RUNNING' && !isActive.value) {
          resume();
        }
      });
  };

  const { t } = useI18n();
  const route = useRoute();

  const rootId = route.params.root_id as string;

  const dbLogRef = ref<InstanceType<typeof DbLog>>();
  const refreshShow = ref(false);
  const logContentRef = ref<HTMLDivElement>();
  /** 当前选中日志版本的信息 */
  const currentData = ref({ version: '' });

  const logState = reactive({
    data: [] as NodeLog[],
    loading: false,
  });

  const currentFailNodeLogIndex = computed(() =>
    props.failedNodes.findIndex((item) => item.data.id === props.node.data.id),
  );
  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));
  const nodeData = computed(() => props.node.data || {});
  const status = computed(() => {
    const themesMap = {
      CREATED: '',
      FAILED: 'danger',
      FINISHED: 'success',
      READY: '',
      RUNNING: 'info',
      SKIPPED: 'danger',
    };

    const status = nodeData.value.status ? nodeData.value.status : 'READY';

    return {
      text: NODE_STATUS_TEXT[status],
      theme: themesMap[status] as '' | 'success' | 'danger' | 'info',
    };
  });
  const STATUS_RUNNING = computed(() => nodeData.value.status === 'RUNNING');
  const STATUS_FAILED = computed(() => nodeData.value.status === 'FAILED');
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
      messageSuccess(t('重试成功'));
      location.reload();
    },
  });
  const { isActive, pause, resume } = useTimeoutPoll(getNodeLogRequest, 5000);
  const { isFullscreen, toggle } = useFullscreen(logContentRef);

  watch(
    () => STATUS_RUNNING.value,
    (isRunning) => {
      if (isRunning && !isActive.value) {
        resume();
      }
      if (!isRunning && isActive.value) {
        pause();
      }
    },
  );

  watch(isShow, () => {
    if (isShow.value) {
      getNodeLogRequest();
      setTimeout(() => {
        dbLogRef.value?.init();
      });
    }
  });

  watch(isFullscreen, () => {
    if (!isFullscreen.value) {
      isShow.value = false;
      setTimeout(() => {
        isShow.value = true;
      });
    }
  });

  const handleClearLog = () => {
    dbLogRef.value?.clearLog();
  };

  /**
   * 下载日志
   */
  const handleDownLoaderLog = () => {
    const messageList = dbLogRef.value!.getValue();
    downloadText(`${nodeData.value.id}.log`, messageList.join('\n'));
  };

  /**
   * 切换日志版本
   */
  const handleChangeDate = (data: ServiceReturnType<typeof getRetryNodeHistories>[number]) => {
    currentData.value = data;
    pause();
    nextTick(() => {
      handleClearLog();
      getNodeLogRequest(true);
    });
  };

  const handleCopyLog = () => {
    const messageList = dbLogRef.value!.getValue();
    execCopy(messageList.join('\n'));
  };

  const handleRefresh = () => {
    refreshShow.value = false;
    runRetryTaskflowNode({
      node_id: props.node.id,
      root_id: rootId,
    });
  };

  const handleClickQuickGoto = (isNext = false) => {
    emits('quickGoto', currentFailNodeLogIndex.value, isNext);
  };

  const handleClose = () => {
    dbLogRef.value!.destroy();
    emits('close');
    pause();
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
      .flex-center();

      .log-header-left {
        flex: 1;
        width: 0;
        padding-right: 8px;
        .flex-center();
      }

      .log-header-info {
        padding-left: 4px;
        font-size: @font-size-normal;
        font-weight: normal;
        flex-shrink: 0;
        .flex-center();
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
    }
  }

  .log-content {
    width: 100%;
    height: 100%;
  }

  .log-tools {
    .flex-center();

    width: 100%;
    height: 42px;
    padding: 0 16px;
    line-height: 42px;
    background: #202024;

    .log-tools-title {
      font-size: 14px;
      color: white;

      span {
        display: inline-block;
        margin-left: 5px;
        color: #c4c6cc;
      }
    }

    .log-tools-bar {
      flex: 1;
      justify-content: flex-end;
      .flex-center();

      i {
        margin-left: 16px;
        font-size: 16px;
        cursor: pointer;
      }
    }
  }
</style>
