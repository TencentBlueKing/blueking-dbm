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
      v-if="prependLoading"
      class="prepend-loading">
      {{ loadingText }}
    </div>
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
    // 向上加载更早内容时的顶部加载态
    prependLoading?: boolean;
  }

  type Emits = (e: 'atTop') => void;

  interface Exposes {
    appendLog: (list: NodeLog[]) => void;
    clearLog: () => void;
    destroy: () => void;
    getValue: () => string[];
    getVisibleRows: () => number;
    init: () => void;
    prependLog: (list: NodeLog[]) => void;
    resizeFit: () => void;
    setLog: (list: NodeLog[]) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    loading: false,
    loadingText: t('日志加载中...'),
    prependLoading: false,
  });

  const emit = defineEmits<Emits>();

  let terminal: Terminal | null;
  let fitAddon: FitAddon | null;
  // 视口是否钉在底部：刚打开为 true，之后由「视口是否在最下方」刷新（onScroll 里统一处理）
  let isPinnedToBottom = true;
  let localLogList: NodeLog[] = [];
  let logicalLineNumbers: number[] = []; // 逻辑行与实际行的映射

  // 清屏 + 清回滚 + 光标归位，必须与内容拼在同一次 write 里原子执行：
  // terminal.clear() 是同步的且会把光标行（最后一行日志）保留在缓冲区顶部，与异步 write 之间会渲染出「最后一行顶到第一行」的闪烁帧
  const CLEAR_SCREEN = '\x1b[2J\x1b[3J\x1b[H';

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
    lastViewportY = -1;

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

  // 最近一次程序化写入（setLog/appendLog/prependLog）的时间戳
  // 写入解析/渲染是异步的，滚动事件可能在标记复位后才补发；用时间窗抑制，与事件到达顺序无关
  let lastWriteAt = 0;
  // 写入后该时间窗内的触顶不算用户主动滚到顶部
  const AT_TOP_SUPPRESS_MS = 300;

  // 上一次检查时的视口位置，模块级同步更新，emit 判断不依赖可能过期的 reactive 状态
  let lastViewportY = -1;
  // 触顶去抖：稳定停留在顶部才触发，瞬时抖动（0↔1 的视口振荡）不算
  let atTopTimer: ReturnType<typeof setTimeout> | undefined;

  /**
   * @param allowEmit 是否允许触发 atTop，由调用点在调用时刻固化意图：
   *   - 追加日志回调传 false（追加引发的滚动不算用户触顶）
   *   - onScroll 默认 true，写入后的时间窗由 lastWriteAt 兜底抑制
   */
  const checkTermScroll = (allowEmit = true) => {
    const buffer = terminal?.buffer.active;
    // 每次现读视口位置，与上次读到的位置做数值对比，不经过任何中间状态
    const viewportY = buffer?.viewportY ?? 0;
    const prevViewportY = lastViewportY;
    lastViewportY = viewportY;

    // isTermAtTop 仅用于 UI（快捷按钮置灰），不参与 emit 判断
    isTermAtTop.value = viewportY === 0;
    isTermAtBottom.value = viewportY + (terminal?.rows || 0) >= (buffer?.length || 0);

    if (atTopTimer) {
      clearTimeout(atTopTimer);
      atTopTimer = undefined;
    }

    // 视口从非顶部位置移动到顶部：停留 150ms 仍稳定在顶部才触发
    // loading 期间内容即将重写、写入后时间窗内的滚动都不算用户主动触顶
    if (
      viewportY === 0 &&
      prevViewportY > 0 &&
      !props.loading &&
      allowEmit &&
      Date.now() - lastWriteAt > AT_TOP_SUPPRESS_MS
    ) {
      atTopTimer = setTimeout(() => {
        const stableY = terminal?.buffer.active.viewportY ?? -1;
        if (stableY === 0 && !props.loading && Date.now() - lastWriteAt > AT_TOP_SUPPRESS_MS) {
          emit('atTop');
        }
      }, 150);
    }
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
    localLogList = list;
    ensureScrollback();
    // 刚打开 / 切换版本都是新内容，定位到最下面
    isPinnedToBottom = true;
    const transferList = formatLogData(list);
    const content = transferList.join('\r\n');
    // 清屏与重写在同一次 write 内原子完成，避免 clear() 与异步 write 之间闪烁
    terminal?.write(`${CLEAR_SCREEN}${content}`, () => {
      lastWriteAt = Date.now();
      fitAddon?.fit();
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
      lastWriteAt = Date.now();
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
      checkTermScroll(false);
    });
  };

  /**
   * 终端一屏的逻辑行数，用于换算「一屏半」的分片条数
   * 按终端可视高度（像素）换算，fit 尚未执行时也能取到准确值；取不到再退回 terminal.rows
   */
  const getVisibleRows = () => fitAddon?.proposeDimensions()?.rows ?? terminal?.rows ?? 0;

  /**
   * 向前插入更早的日志
   * xterm 只能在缓冲区末尾追加，向上插入只能整段重写：
   * 清屏后按「更早内容 + 已有内容」顺序原子重放，再把视口定位到新加载内容的最后一条
   */
  const handlePrependLog = (list: NodeLog[] = []) => {
    if (!list.length || !terminal) {
      return;
    }

    const oldBufferLength = terminal.buffer.active.length;

    localLogList = [...list, ...localLogList];
    ensureScrollback();

    // 清屏与重写在同一次 write 内原子完成，避免 clear() 与异步 write 之间出现「最后一行顶到第一行」的闪烁
    terminal?.write(`${CLEAR_SCREEN}${formatLogData(localLogList).join('\r\n')}`, () => {
      lastWriteAt = Date.now();
      // 旧内容逐字节相同，其在新缓冲区中的整体偏移 = 新片占用的行数，新片占 [0, delta)
      const delta = (terminal?.buffer.active.length ?? 0) - oldBufferLength;
      // 视口最后一行 = 新加载内容的最后一条；新片不足一屏时贴顶
      const targetY = Math.max(delta - (terminal?.rows ?? 0), 0);
      terminal?.scrollToLine(targetY);
      updateLogicalLineNumbers();
      updateLineNumbers();
      checkTermScroll(false);
    });
  };

  const destroyTerm = () => {
    isPinnedToBottom = true;
    if (atTopTimer) {
      clearTimeout(atTopTimer);
      atTopTimer = undefined;
    }
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
    // fit 引发的视口变化不是用户滚动
    checkTermScroll(false);
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
    prependLog: handlePrependLog,
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
      z-index: 1;
      display: flex;
      width: 100%;
      height: 100%;
      justify-content: center;
      align-items: center;
      // 半透明遮罩：盖住底层日志内容，突出加载态
      background: rgb(26 26 26 / 25%);

      .bk-loading-indicator {
        align-items: center;
      }
    }

    // 向上加载更早内容的顶部条：字号字体颜色与日志内容一致
    .prepend-loading {
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
      z-index: 1;
      display: flex;
      height: 32px;
      font-family: Consolas, monospace;
      font-size: 12px;
      color: #c4c6cc;
      background: rgb(26 26 26 / 90%);
      align-items: center;
      justify-content: center;
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
