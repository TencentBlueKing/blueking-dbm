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
  <div class="db-log-main">
    <div
      v-if="loading"
      class="loading-main">
      <BkLoading
        :loading="loading"
        mode="spin"
        :title="loadingText">
      </BkLoading>
    </div>
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
</template>

<script setup lang="tsx">
  import { execCopy } from '@utils';

  import { t } from '@locales/index';

  import { FitAddon } from '@xterm/addon-fit';
  import { WebLinksAddon } from '@xterm/addon-web-links';
  import { type IBuffer, Terminal } from '@xterm/xterm';

  import { formatLogData, type NodeLog } from './utils';

  interface Props {
    loading?: boolean;
    loadingText?: string;
  }

  interface Exposes {
    appendLog: (list: NodeLog[]) => void;
    clearLog: () => void;
    destroy: () => void;
    getValue: () => string[];
    getVisibleRows: () => number;
    init: () => void;
    resizeFit: () => void;
    setLog: (list: NodeLog[]) => void;
  }

  withDefaults(defineProps<Props>(), {
    loading: false,
    loadingText: t('日志加载中...'),
  });

  let terminal: Terminal | null;
  let fitAddon: FitAddon | null;
  // 视口是否钉在底部：刚打开为 true，之后由「视口是否在最下方」刷新（onScroll 里统一处理）
  let isPinnedToBottom = true;
  let localLogList: NodeLog[] = [];
  let logicalLineNumbers: number[] = []; // 逻辑行与实际行的映射

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
    });
    fitAddon = new FitAddon();
    const linkAddon = new WebLinksAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(linkAddon);
    terminal.open(document.getElementById('nodeLogTermContent')!);

    // 劫持键盘事件
    terminal.attachCustomKeyEventHandler((e) => {
      if ((e.ctrlKey || e.metaKey) && e.code === 'KeyC' && e.type === 'keydown') {
        const selection = terminal?.getSelection();
        if (selection) {
          execCopy(selection);
          return false; // 阻止默认
        }
      }
      return true;
    });

    terminal.onScroll(() => {
      const buffer = terminal?.buffer.active;
      // 程序滚动落点与状态一致（钉底滚到底、恢复滚到原位置），统一按「视口是否在最下方」刷新即可
      isPinnedToBottom = (buffer?.viewportY || 0) + (terminal?.rows || 0) >= (buffer?.length || 0);
      updateLineNumbers();
      checkTermScroll();
    });
  };

  const isTermAtTop = ref(false);
  const isTermAtBottom = ref(false);

  const updateLogicalLineNumbers = () => {
    const buffer = terminal?.buffer.active || ([] as unknown as IBuffer);
    logicalLineNumbers = [];
    let currentLogicalLine = 0;
    if (!buffer.length) {
      return;
    }

    for (let i = 0; i < buffer.length; i++) {
      const line = buffer!.getLine(i);
      if (line && !line.isWrapped) {
        currentLogicalLine = currentLogicalLine + 1; // 行号从1开始
      }
      logicalLineNumbers[i] = currentLogicalLine;
    }
  };

  // 更新行号函数
  const updateLineNumbers = () => {
    const lineNumbers = document.getElementById('nodeLogLineNumbers')!;
    const activeBuffer = terminal?.buffer.active;
    const scrollTop = activeBuffer?.viewportY || 0;
    const visibleRows = terminal?.rows || 0;
    // 生成当前可见行的行号
    let numbersHtml = '';
    let isSameLine = false;
    for (let i = 0; i < visibleRows; i++) {
      const lineIndex = scrollTop + i;
      isSameLine = logicalLineNumbers[lineIndex] === logicalLineNumbers[lineIndex - 1];
      const logicalLine = !isSameLine ? (logicalLineNumbers[lineIndex] ?? '') : '';
      numbersHtml += `<div class="line-num">${logicalLine}</div>`;
    }
    lineNumbers.innerHTML = numbersHtml;
  };

  const checkTermScroll = () => {
    isTermAtTop.value = terminal?.buffer.active.viewportY === 0;
    const buffer = terminal?.buffer.active;
    isTermAtBottom.value = (buffer?.viewportY || 0) + (terminal?.rows || 0) >= (buffer?.length || 0);
  };

  const handleClearLog = () => {
    terminal?.clear();
    // 清空后是新的一份日志视图，重新钉在底部
    isPinnedToBottom = true;
  };

  const handleTermToTop = () => {
    terminal?.scrollToTop();
  };

  const handleTermToBottom = () => {
    terminal?.scrollToBottom();
  };

  /**
   * 保证缓冲区能装下已加载的全部日志
   * scrollback 不足时顶部会被持续裁剪：行号被截断、用户滚动位置也无法保持
   * 容量 = scrollback + 视口行数，需覆盖已加载的全部行
   */
  const ensureScrollback = () => {
    if (!terminal) {
      return;
    }
    const required = localLogList.length + 10;
    if ((terminal.options.scrollback ?? 0) < required) {
      terminal.options.scrollback = required;
    }
  };

  /**
   * 设置日志（切换版本 / 全屏重放）
   */
  const handleSetLog = (list: NodeLog[] = []) => {
    handleClearLog();
    localLogList = list;
    ensureScrollback();
    const transferList = formatLogData(list);
    const content = transferList.join('\r\n');
    // write 是异步解析，滚动调整必须在回调里做（此时数据才真正进入缓冲区）
    terminal?.write(content, () => {
      fitAddon?.fit();
      // 刚打开 / 切换版本都是新内容，定位到最下面
      if (isPinnedToBottom) {
        terminal?.scrollToBottom();
      }
      updateLogicalLineNumbers();
      updateLineNumbers();
      checkTermScroll();
    });
  };

  /**
   * 追加日志
   * 不清屏，仅写入新增分片：
   * - 视口钉在底部：每次追加后自动滚动到最下面
   * - 用户滚动查看：保持视口行号不变（scrollback 已覆盖全量，不会因裁剪产生行号偏移）
   */
  const handleAppendLog = (list: NodeLog[] = []) => {
    if (!list.length) {
      return;
    }

    // 已有内容时先换行，避免本片第一行拼在上一片最后一行的行尾
    const hasPrevious = localLogList.length > 0;
    localLogList = [...localLogList, ...list];
    ensureScrollback();

    const content = `${hasPrevious ? '\r\n' : ''}${formatLogData(list).join('\r\n')}`;
    // write 是异步解析，滚动调整必须在回调里做（此时数据才真正进入缓冲区）
    const anchorY = terminal?.buffer.active.viewportY ?? 0;
    terminal?.write(content, () => {
      if (isPinnedToBottom) {
        terminal?.scrollToBottom();
      } else {
        const buffer = terminal?.buffer.active;
        // 扩容等导致的行号偏移，恢复到用户原本所在位置
        if (buffer && anchorY !== buffer.viewportY) {
          terminal?.scrollToLine(anchorY);
        }
      }
      updateLogicalLineNumbers();
      updateLineNumbers();
      checkTermScroll();
    });
  };

  /**
   * 终端一屏的逻辑行数，用于换算「一屏半」的分片条数
   * 按终端可视高度（像素）换算，fit 尚未执行时也能取到准确值；取不到再退回 terminal.rows
   */
  const getVisibleRows = () => fitAddon?.proposeDimensions()?.rows ?? terminal?.rows ?? 0;

  const destroyTerm = () => {
    isPinnedToBottom = true;
    terminal?.clear();
    terminal?.dispose();
    fitAddon?.dispose();
    terminal = null;
    fitAddon = null;
    const lineNumbers = document.getElementById('nodeLogLineNumbers')!;
    lineNumbers.innerHTML = '';
  };

  const handleWindowResize = () => {
    fitAddon?.fit();
    updateLogicalLineNumbers();
    updateLineNumbers();
    checkTermScroll();
  };

  onMounted(() => {
    window.addEventListener('resize', handleWindowResize);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', handleWindowResize);
  });

  defineExpose<Exposes>({
    appendLog: handleAppendLog,
    clearLog: handleClearLog,
    destroy: destroyTerm,
    getValue() {
      return formatLogData(localLogList, false);
    },
    getVisibleRows,
    init: initTerm,
    resizeFit() {
      fitAddon?.fit();
    },
    setLog: handleSetLog,
  });
</script>
<style lang="less">
  .db-log-main {
    position: relative;
    display: flex;
    width: 100%;
    height: 100%;
    padding-top: 12px;
    background-color: #1a1a1a;

    #nodeLogLineNumbers {
      width: 64px;
      overflow: hidden;
      font-family: Consolas, monospace;
      font-size: 12px;
      color: #979ba5;
      user-select: none;

      .line-num {
        width: 100%;
        height: 14px;
        text-align: center;
      }
    }

    #nodeLogTermContent {
      flex: 1;
      height: 100%;
    }

    .loading-main {
      position: absolute;
      display: flex;
      width: 100%;
      height: 100%;
      justify-content: center;
      align-items: center;

      .bk-loading-indicator {
        align-items: center;
      }
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

  .xterm .xterm-rows > div:hover {
    cursor: pointer;
    background: #292929;
  }
</style>
