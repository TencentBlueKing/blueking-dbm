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
  import _ from 'lodash';

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
  let isAutoScrollEnabled = true; // 默认开启自动滚动
  let lastScrollPosition = 0; // 记录上次滚动位置
  let localLogList: NodeLog[] = [];
  let logicalLineNumbers: number[] = []; // 逻辑行与实际行的映射
  let ignoreLineFlags: boolean[] = []; // 标记不展示行号的逻辑行（ignore_line 条目）

  /**
   * 按条目顺序生成「逻辑行是否忽略行号」的标记
   * 每条日志按换行拆成若干物理行，顺序与终端 buffer 的逻辑行一一对应（自动换行只产生 isWrapped 行）；
   * 末尾空段是下一条日志的起始行（写入时不会额外补换行），不计入
   */
  const buildIgnoreLogicalFlags = () => {
    const flags: boolean[] = [];
    localLogList.forEach((item) => {
      const text = formatLogData([item])[0] ?? '';
      const segments = text.split(/\r\n|\r|\n/);
      segments.forEach((segment, index) => {
        if (index === segments.length - 1 && segment === '') {
          return;
        }
        flags.push(Boolean(item['ignore_line']));
      });
    });
    return flags;
  };

  const updateLastScrollPosition = _.debounce(() => {
    lastScrollPosition = terminal?.buffer.active.viewportY || 0;
  }, 500);

  const initTerm = () => {
    terminal = new Terminal({
      convertEol: false,
      disableStdin: true,
      fontFamily: 'Consolas, monospace',
      fontSize: 12,
      lineHeight: 1,
      // 日志可能多达 10MB（约 10~20 万行），scrollback 太小会导致历史行被丢弃
      scrollback: 200000,
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
    lastScrollPosition = terminal.buffer.active.viewportY;

    const originalWrite = terminal.writeln;
    terminal.write = function (data: string) {
      originalWrite.call(this, data);
      // 仅当用户未手动滚动时自动跳转到底部
      if (isAutoScrollEnabled) {
        terminal?.scrollToBottom();
      } else {
        // 维持用户手动定位的位置
        setTimeout(() => {
          terminal?.scrollToLine(lastScrollPosition);
        });
      }
    };

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

    terminal.attachCustomWheelEventHandler(() => {
      updateLastScrollPosition();
      return true;
    });

    terminal.onScroll(() => {
      const buffer = terminal?.buffer.active;
      isAutoScrollEnabled = (buffer?.viewportY || 0) + (terminal?.rows || 0) >= (buffer?.length || 0);
      updateLineNumbers();
      checkTermScroll();
    });
  };

  const isTermAtTop = ref(false);
  const isTermAtBottom = ref(false);

  const updateLogicalLineNumbers = () => {
    const buffer = terminal?.buffer.active || ([] as unknown as IBuffer);
    logicalLineNumbers = [];
    ignoreLineFlags = [];
    let currentLogicalLine = 0;
    if (!buffer.length) {
      return;
    }

    const ignoreLogicalFlags = buildIgnoreLogicalFlags();
    let logicalIndex = -1;

    for (let i = 0; i < buffer.length; i++) {
      const line = buffer!.getLine(i);
      if (line && !line.isWrapped) {
        logicalIndex += 1;
        // ignore_line 行不占用行号：沿用上一行号且在渲染时置空
        if (ignoreLogicalFlags[logicalIndex]) {
          ignoreLineFlags[i] = true;
          logicalLineNumbers[i] = currentLogicalLine;
          continue;
        }
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
      const logicalLine = !isSameLine && !ignoreLineFlags[lineIndex] ? (logicalLineNumbers[lineIndex] ?? '') : '';
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
  };

  const handleTermToTop = () => {
    terminal?.scrollToTop();
    lastScrollPosition = 0;
  };

  const handleTermToBottom = () => {
    terminal?.scrollToBottom();
  };

  /**
   * 设置日志
   */
  const handleSetLog = (list: NodeLog[] = []) => {
    handleClearLog();
    localLogList = list;
    const transferList = formatLogData(list);
    const content = transferList.join('\r\n');
    terminal?.write(content);
    setTimeout(() => {
      fitAddon?.fit();
      updateLogicalLineNumbers();
      updateLineNumbers();
      checkTermScroll();
    });
  };

  /**
   * 追加日志：不清空已有内容，只往后写新条目（轮询增量场景）
   * 不额外补换行，条目自带的换行即分隔，避免出现空行
   */
  const handleAppendLog = (list: NodeLog[] = []) => {
    if (list.length === 0) {
      return;
    }
    localLogList = [...localLogList, ...list];
    const content = formatLogData(list).join('\r\n');
    // 用户不在底部（顶部或中间）时保持当前视口不动，只有停在底部才跟随新日志
    if (terminal) {
      const buffer = terminal.buffer.active;
      const isAtBottom = buffer.viewportY + terminal.rows >= buffer.length;
      if (!isAtBottom) {
        isAutoScrollEnabled = false;
        lastScrollPosition = buffer.viewportY;
      }
    }
    terminal?.write(content);
    setTimeout(() => {
      updateLogicalLineNumbers();
      updateLineNumbers();
      checkTermScroll();
    });
  };

  const destroyTerm = () => {
    isAutoScrollEnabled = true;
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
