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
        :title="t('日志加载中...')">
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
  import { format } from 'date-fns';
  import { useI18n } from 'vue-i18n';
  import { FitAddon } from 'xterm-addon-fit';
  import { WebLinksAddon } from 'xterm-addon-web-links';

  import { execCopy } from '@utils';

  import { Terminal } from '@xterm/xterm';

  interface Props {
    loading?: boolean;
  }

  interface NodeLog {
    levelname: string;
    message: string;
    timestamp: number;
  }

  interface Exposes {
    clearLog: () => void;
    destroy: () => void;
    getValue: () => string[];
    init: () => void;
    resizeFit: () => void;
    setLog: (list: NodeLog[]) => void;
  }

  withDefaults(defineProps<Props>(), {
    loading: false,
  });

  let terminal: Terminal;
  let fitAddon: FitAddon;
  let isAutoScrollEnabled = true; // 默认开启自动滚动
  let lastScrollPosition = 0; // 记录上次滚动位置
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
      windowsMode: false,
    });
    fitAddon = new FitAddon();
    const linkAddon = new WebLinksAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(linkAddon);
    terminal.open(document.getElementById('nodeLogTermContent')!);
    const viewport = terminal.element!.querySelector('.xterm-viewport')!;
    lastScrollPosition = terminal.buffer.active.viewportY;

    const originalWrite = terminal.writeln;
    terminal.write = function (data: string) {
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
        lastScrollPosition = terminal.buffer.active.viewportY;
      });
      return true;
    });

    terminal.element!.querySelector('.xterm-viewport')!.addEventListener('scroll', () => {
      isAutoScrollEnabled = viewport.scrollTop >= viewport.scrollHeight - viewport.clientHeight;
      updateLineNumbers();
      checkTermScroll();
    });
  };

  const { t } = useI18n();

  const isTermAtTop = ref(false);
  const isTermAtBottom = ref(false);

  const updateLogicalLineNumbers = () => {
    const buffer = terminal.buffer.active;
    logicalLineNumbers = [];
    let currentLogicalLine = 1;

    for (let i = 0; i < buffer.length; i++) {
      const line = buffer.getLine(i);
      if (line && !line.isWrapped) {
        currentLogicalLine = i + 1; // 行号从1开始
      }
      logicalLineNumbers[i] = currentLogicalLine;
    }
  };

  // 更新行号函数
  const updateLineNumbers = () => {
    const lineNumbers = document.getElementById('nodeLogLineNumbers')!;
    const activeBuffer = terminal.buffer.active;
    const scrollTop = activeBuffer.viewportY;
    const visibleRows = terminal.rows;
    // 生成当前可见行的行号
    let numbersHtml = '';
    let isSameLine = false;
    for (let i = 0; i < visibleRows; i++) {
      const lineIndex = scrollTop + i;
      isSameLine = logicalLineNumbers[lineIndex] === logicalLineNumbers[lineIndex - 1];
      const logicalLine = !isSameLine ? logicalLineNumbers[lineIndex] : '';
      const lineText = activeBuffer.getLine(lineIndex)?.translateToString().trim();
      if (lineText) {
        numbersHtml += `<div class="line-num">${logicalLine}</div>`;
      }
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

      // if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} info\]/.test(rowText)) {
      //   return `\x1b[32m${rowText}\x1b[0m`;
      // }

      if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} warn\]/i.test(rowText)) {
        return `\x1b[33m${rowText}\x1b[0m`;
      }

      if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} error\]/i.test(rowText)) {
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
  const handleSetLog = (list: NodeLog[] = []) => {
    localLogList = list;
    const transferList = formatLogData(list);
    const content = transferList.join('\r\n');
    terminal.write(content);
    setTimeout(() => {
      fitAddon.fit();
      updateLogicalLineNumbers();
      updateLineNumbers();
      checkTermScroll();
    });
  };

  const destroyTerm = () => {
    isAutoScrollEnabled = true;
    terminal.clear();
    terminal.dispose();
    fitAddon.dispose();
  };

  const handleWindowResize = () => {
    fitAddon.fit();
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
    clearLog: handleClearLog,
    destroy: destroyTerm,
    getValue() {
      return formatLogData(localLogList, false);
    },
    init: initTerm,
    resizeFit() {
      fitAddon.fit();
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
