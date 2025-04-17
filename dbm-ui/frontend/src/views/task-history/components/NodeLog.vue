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
            <span> {{ t('日志保留7天_如需要请下载保存') }}</span>
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
        <div
          class="log-details"
          :style="{ height: isFullscreen ? 'calc(100% - 42px)' : '100%' }">
          <div id="nodeLogLineNumbers"></div>
          <div id="nodeLogTermContent"></div>
          <div class="quick-switch">
            <div
              class="icon-box"
              :class="{ 'is-disabled': isTermAtTop }"
              @click="handleTermToTop">
              <DbIcon type="top-huidaodingbu" />
            </div>
            <div
              class="icon-box"
              :class="{ 'is-disabled': isTermAtBottom }"
              @click="handleTermToBottom">
              <DbIcon type="top-huidaodibu" />
            </div>
          </div>
        </div>
      </div>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { format } from 'date-fns';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { FitAddon } from 'xterm-addon-fit';
  import { WebLinksAddon } from 'xterm-addon-web-links';

  import { getNodeLog, getRetryNodeHistories, retryTaskflowNode } from '@services/source/taskflow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { downloadText, execCopy, messageSuccess } from '@utils';

  import { useFullscreen, useTimeoutPoll } from '@vueuse/core';
  import { Terminal } from '@xterm/xterm';

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

  const initTerm = () => {
    terminal = new Terminal({
      convertEol: false,
      disableStdin: true,
      fontFamily: 'Consolas, monospace',
      fontSize: 12,
      lineHeight: 1,
      scrollback: 1000,
      theme: {
        background: '#1A1A1A', // 背景色
        foreground: '#C4C6CC', // 默认字体颜色
      },
      windowsMode: false,
    });
    fitAddon = new FitAddon();
    const linkAddon = new WebLinksAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(linkAddon);
    terminal.open(document.getElementById('nodeLogTermContent')!);
    const viewport = terminal.element!.querySelector('.xterm-viewport')!;
    lastScrollPosition = terminal.buffer.active.viewportY;

    const originalWrite = terminal.write;
    terminal.write = function (data) {
      originalWrite.call(this, data);
      // 仅当用户未手动滚动时自动跳转到底部
      if (isAutoScrollEnabled) {
        terminal.scrollToBottom();
      } else {
        // 维持用户手动定位的位置
        setTimeout(() => {
          terminal.scrollToLine(lastScrollPosition);
        });
      }
    };

    // 劫持键盘事件
    terminal.attachCustomKeyEventHandler((e) => {
      if ((e.ctrlKey || e.metaKey) && e.code === 'KeyC' && e.type === 'keydown') {
        const selection = terminal.getSelection();
        if (selection) {
          execCopy(selection);
          return false; // 阻止默认
        }
      }
      return true;
    });

    terminal.attachCustomWheelEventHandler(() => {
      setTimeout(() => {
        lastScrollPosition = isScrollDown ? terminal.buffer.active.viewportY + 7 : terminal.buffer.active.viewportY - 7;
      });
      return true;
    });

    terminal.element!.querySelector('.xterm-viewport')!.addEventListener('scroll', () => {
      isScrollDown = terminal.buffer.active.viewportY > currentScrollPosition;
      currentScrollPosition = terminal.buffer.active.viewportY;
      isAutoScrollEnabled = viewport.scrollTop >= viewport.scrollHeight - viewport.clientHeight;
      updateLineNumbers();
      checkTermScroll();
    });
  };

  const getNodeLogRequest = (isInit?: boolean) => {
    if (!currentData.value.version) {
      return;
    }

    const params = {
      node_id: nodeData.value.id,
      root_id: rootId,
      version_id: currentData.value.version,
    };
    getNodeLog(params)
      .then((data) => {
        logState.data = data;
        handleClearLog();
        handleSetLog(formatLogData(data));
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
  let terminal: Terminal;
  let fitAddon: FitAddon;
  let isAutoScrollEnabled = true; // 默认开启自动滚动
  let lastScrollPosition = 0; // 记录上次滚动位置
  let currentScrollPosition = 0; // 用来判断滚动条的滚动方向
  let isScrollDown = false;

  const refreshShow = ref(false);
  const logContentRef = ref<HTMLDivElement>();
  const isTermAtTop = ref(false);
  const isTermAtBottom = ref(false);
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
        initTerm();
      });
    }
  });

  watch(isFullscreen, () => {
    if (isFullscreen.value) {
      setTimeout(() => {
        fitAddon.fit();
      });
    } else {
      isShow.value = false;
      setTimeout(() => {
        isShow.value = true;
      });
    }
  });

  // 更新行号函数
  const updateLineNumbers = () => {
    const lineNumbers = document.getElementById('nodeLogLineNumbers')!;
    const buffer = terminal.buffer.active;
    const startLine = buffer.viewportY + 1;
    const endLine = startLine + terminal.rows - 1;

    let numbersHtml = '';
    for (let i = startLine; i <= endLine; i++) {
      numbersHtml += `<div class="line-num">${i}</div>`;
    }
    lineNumbers.innerHTML = numbersHtml;
  };

  const checkTermScroll = () => {
    isTermAtTop.value = terminal.buffer.active.viewportY === 0;
    const buffer = terminal.buffer.active;
    isTermAtBottom.value = buffer.viewportY + terminal.rows >= buffer.length;
  };

  const handleClearLog = () => {
    terminal.clear();
  };

  const formatLogData = (data: NodeLog[] = [], isSetColor = true) => {
    const regex = /^##\[[a-z]+]/;
    return data.map((item) => {
      const { levelname, message, timestamp } = item;
      const time = format(new Date(Number(timestamp)), 'yyyy-MM-dd HH:mm:ss');
      let rowText = regex.test(message)
        ? message.replace(regex, (match: string) => `${match}[${time} ${levelname}]`)
        : `[${time} ${levelname}] ${message}`;
      rowText = rowText.replace(/\n/g, '\r\n');
      if (!isSetColor) {
        return rowText;
      }

      if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} info\]/.test(rowText)) {
        return `\x1b[32m${rowText}\x1b[0m`;
      }

      if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} warn\]/.test(rowText)) {
        return `\x1b[33m${rowText}\x1b[0m`;
      }

      if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} error\]/.test(rowText)) {
        return `\x1b[31m${rowText}\x1b[0m`;
      }

      return rowText;
    });
  };

  const handleTermToTop = () => {
    terminal.scrollToTop();
    lastScrollPosition = 0;
  };

  const handleTermToBottom = () => {
    terminal.scrollToBottom();
  };

  /**
   * 设置日志
   */
  const handleSetLog = (list: string[]) => {
    const str = list.join('\r\n');
    terminal.write(str);
    setTimeout(() => {
      fitAddon.fit();
      updateLineNumbers();
      checkTermScroll();
    });
  };

  /**
   * 下载日志
   */
  const handleDownLoaderLog = () => {
    const messageList = formatLogData(logState.data, false);
    downloadText(`${nodeData.value.id}.log`, messageList.join('\n'));
  };

  /**
   * 切换日志版本
   */
  const handleChangeDate = (data: ServiceReturnType<typeof getRetryNodeHistories>[number]) => {
    currentData.value = data;
    pause();
    nextTick(() => {
      logState.loading = true;
      handleClearLog();
      getNodeLogRequest(true);
    });
  };

  const handleCopyLog = () => {
    const messageList = formatLogData(logState.data, false);
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
    isAutoScrollEnabled = true;
    terminal.clear();
    terminal.dispose();
    fitAddon.dispose();
    emits('close');
    pause();
  };

  const handleWindowResize = () => {
    fitAddon.fit();
    updateLineNumbers();
    checkTermScroll();
  };

  onMounted(() => {
    window.addEventListener('resize', handleWindowResize);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', handleWindowResize);
  });
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

  .log-details {
    position: relative;
    display: flex;
    width: 100%;
    background-color: #1a1a1a;

    #nodeLogLineNumbers {
      width: 64px;
      overflow: hidden;
      font-family: Consolas, monospace;
      font-size: 12px;
      color: #979ba5;
      user-select: none;

      :deep(.line-num) {
        width: 100%;
        height: 14px;
        text-align: center;
      }
    }

    #nodeLogTermContent {
      flex: 1;
      height: 100%;
    }

    .quick-switch {
      position: absolute;
      right: 6px;
      bottom: 4px;
      display: flex;
      width: 24px;
      flex-direction: column;
      cursor: pointer;
      gap: 4px;

      .icon-box {
        display: flex;
        width: 24px;
        height: 24px;
        color: #c4c6cc;
        background-color: #4d4d4d;
        align-items: center;
        justify-content: center;

        &.is-disabled {
          color: #c4c6cc33;
        }
      }
    }
  }
</style>
<style lang="less">
  .xterm .xterm-rows > div:hover {
    cursor: pointer;
    background: rgb(255 215 0 / 30%);
  }
</style>
