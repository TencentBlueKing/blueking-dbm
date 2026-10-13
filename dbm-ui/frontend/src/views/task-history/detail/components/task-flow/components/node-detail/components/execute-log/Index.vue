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
  <div
    ref="logContentRef"
    class="log-content">
    <div class="log-tools">
      <div class="log-tools-title">
        <DbIcon
          :style="{ color: statusInfo.color }"
          :type="statusInfo.icon" />
        <span class="main-title">{{ statusInfo.text }}</span>
        <span class="tip"> {{ t('日志保留30天_如需要请下载保存') }}</span>
      </div>
      <div
        class="log-tools-bar"
        :class="{ 'is-loading': logState.loading }">
        <ExecuteHistory
          v-if="isShow"
          :node-id="nodeData.id"
          :root-id="rootId"
          @change="handleChangeDate" />
        <DbIcon
          v-bk-tooltips="t('复制')"
          type="copy"
          @click="handleCopyLog" />
        <DbIcon
          v-bk-tooltips="t('下载')"
          type="import"
          @click="handleDownLoaderLog" />
        <DbIcon
          v-bk-tooltips="screenIcon.text"
          :type="screenIcon.icon"
          @click="toggle" />
      </div>
    </div>
    <DbLog
      ref="dbLogRef"
      :loading="logState.loading"
      :loading-text="autoOpenAiLog ? t('日志加载中，加载完成将自动解析日志') : t('日志加载中...')"
      :prepend-loading="logState.prependLoading"
      style="height: calc(100% - 42px)"
      @at-top="handleLogAtTop" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getNodeLog, getRetryNodeHistories } from '@services/source/taskflow';

  import DbLog from '@components/db-log/index.vue';

  import {
    type FlowNode,
    getNodeDisplayStatus,
    NODE_STATUS_META,
    type NodeDisplayStatus,
  } from '@views/task-history/detail/utils';

  import { downloadText, execCopy } from '@utils';

  import { useFullscreen, useTimeoutFn, useTimeoutPoll } from '@vueuse/core';

  import ExecuteHistory from './components/ExecuteHistory.vue';

  type NodeLogItem = ServiceReturnType<typeof getNodeLog>['results'][number];

  interface Props {
    autoOpenAiLog: boolean;
    isShow?: boolean;
    node?: FlowNode;
    rootId?: string;
  }

  type Emits = (e: 'versionChange', version: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    node: () => ({}) as NonNullable<Props['node']>,
    rootId: '',
  });
  const emits = defineEmits<Emits>();

  // 终端尚未完成 fit 时的分片条数下限，避免发出 limit 为 0 的空请求
  const MIN_LOG_PAGE_SIZE = 30;
  // 后端单次拉取上限
  const MAX_LOG_PAGE_SIZE = 10000;

  const { t } = useI18n();

  // 图标与配色。文案统一取公共状态表，配色单独定：这条工具栏是深底，执行中、准备中和待执行用灰色更清楚
  const STATUS_ICON_MAP: Record<NodeDisplayStatus, { color: string; icon: string }> = {
    CREATED: { color: '#979BA5', icon: 'waiting-shalou' },
    FAILED: { color: NODE_STATUS_META.FAILED.color, icon: 'delete-fill' },
    FINISHED: { color: NODE_STATUS_META.FINISHED.color, icon: 'check' },
    READY: { color: '#979BA5', icon: 'loading' },
    RUNNING: { color: '#979BA5', icon: 'loading' },
    SKIPPED: { color: NODE_STATUS_META.SKIPPED.color, icon: 'check' },
    TODO: { color: NODE_STATUS_META.TODO.color, icon: 'dengdaiqueren' },
  };

  const dbLogRef = ref<InstanceType<typeof DbLog>>();
  const logContentRef = ref<HTMLDivElement>();
  const currentData = ref({ version: '' });

  const logState = reactive({
    data: [] as NodeLogItem[],
    loading: false,
    prependLoading: false,
  });

  // 日志版本与生命周期令牌，用于丢弃已过期分片的返回
  let logToken = 0;
  // 上一片返回的游标，为空表示没有下一片（更早内容）
  let prevSearchAfter: (number | string)[] = [];
  // 是否还有更早内容（has_data）
  let hasMorePrev = false;

  /**
   * 分片条数取终端「一屏半」（按逻辑行计，不折算行），不超过后端单次上限
   */
  const getLogPageSize = () => {
    const rows = dbLogRef.value?.getVisibleRows() ?? 0;
    return Math.min(Math.max(Math.ceil(rows * 1.5), MIN_LOG_PAGE_SIZE), MAX_LOG_PAGE_SIZE);
  };

  const getNodeLogParams = () => ({
    limit: getLogPageSize(),
    node_id: nodeData.value.id,
    root_id: props.rootId,
    version_id: currentData.value.version,
  });

  /**
   * 首片加载：只拉尾部最新的分片，更早内容由用户滚动到顶部时按需加载
   */
  const fetchFirstChunk = async (token: number) => {
    const page = await getNodeLog(getNodeLogParams());
    // 请求可能在切换版本或组件卸载后才返回
    if (token !== logToken) {
      return;
    }

    prevSearchAfter = page.search_after;
    hasMorePrev = page.has_data === true;
    const chunk = page.results;
    logState.data = chunk;
    dbLogRef.value?.setLog(chunk);
  };

  const itemKey = (item: NodeLogItem) => `${item.timestamp}|${item.message}`;

  /**
   * 运行中增量：重新请求首片，比对出比已加载更新的条目后追加
   */
  const fetchNewLogs = async (token: number) => {
    const page = await getNodeLog(getNodeLogParams());
    if (token !== logToken) {
      return;
    }

    prevSearchAfter = page.search_after;
    hasMorePrev = page.has_data === true;
    const chunk = page.results;
    if (!chunk.length) {
      return;
    }

    const lastItem = logState.data[logState.data.length - 1];
    if (!lastItem) {
      logState.data = chunk;
      dbLogRef.value?.setLog(chunk);
      return;
    }

    // 从尾部找已加载最后一条在首片中的位置，其后即为新增
    const lastKeyIdx = chunk.map(itemKey).lastIndexOf(itemKey(lastItem));
    // 找不到重叠点时（新增量超过分片窗口）放弃本次追加，避免写入重复内容
    const fresh = lastKeyIdx >= 0 ? chunk.slice(lastKeyIdx + 1) : [];
    if (!fresh.length) {
      return;
    }

    logState.data.push(...fresh);
    // 追加引发的「离顶→回顶」滚动事件可能延迟到达，记录时间供 handleLogAtTop 拦截
    lastAppendAt = Date.now();
    dbLogRef.value?.appendLog(fresh);
  };

  /**
   * 向上加载更早内容：视口触顶且后端还有下一片时触发
   */
  const fetchPrevChunk = async (token: number) => {
    if (!hasMorePrev || logState.prependLoading || logState.loading) {
      return;
    }
    logState.prependLoading = true;
    try {
      const page = await getNodeLog({
        ...getNodeLogParams(),
        search_after: prevSearchAfter,
      });
      if (token !== logToken) {
        return;
      }

      prevSearchAfter = page.search_after;
      hasMorePrev = page.has_data === true;
      const chunk = page.results;
      if (!chunk.length) {
        return;
      }

      logState.data = [...chunk, ...logState.data];
      dbLogRef.value?.prependLog(chunk);
    } finally {
      if (token === logToken) {
        logState.prependLoading = false;
      }
    }
  };

  // 追加日志后的该时间窗内，atTop 一律视为写入引发的滚动而非用户触顶
  const APPEND_AT_TOP_SUPPRESS_MS = 500;
  let lastAppendAt = 0;

  const handleLogAtTop = () => {
    if (Date.now() - lastAppendAt < APPEND_AT_TOP_SUPPRESS_MS) {
      return;
    }
    fetchPrevChunk(logToken);
  };

  const getNodeLogRequest = (isInit?: boolean) => {
    if (!currentData.value.version) {
      return Promise.resolve();
    }

    // 日志区为空时展示加载遮罩，首片渲染后即关闭
    if (isInit) {
      logState.loading = true;
    }

    const token = (logToken += 1);

    return (
      fetchFirstChunk(token)
        // 报错提示已由请求层统一给出。这里必须吞掉：useTimeoutPoll 的回调一旦抛错，轮询就再也不会续上
        .catch(() => {})
        .finally(() => {
          if (token !== logToken) {
            return;
          }
          logState.loading = false;
          if (isInit && nodeData.value.status === 'RUNNING' && !isActive.value) {
            resume();
          }
        })
    );
  };

  /**
   * 轮询与节点结束补拉都走增量比对
   * 向上加载/首片加载进行中不追加：重写解析需数秒，交叉写入会打乱视口位置
   */
  const pollNewLogs = () => {
    if (logState.prependLoading || logState.loading) {
      return;
    }
    fetchNewLogs(logToken).catch(() => {});
  };

  /**
   * 中断在途分片并清空日志，用于切换执行记录版本与关闭侧滑
   */
  const resetLogState = () => {
    logToken += 1;
    prevSearchAfter = [];
    hasMorePrev = false;
    logState.data = [];
    logState.loading = false;
    logState.prependLoading = false;
    dbLogRef.value?.setLog([]);
  };

  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'un-full-screen' : 'full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));
  const nodeData = computed(() => props.node);

  const isRunning = computed(() => nodeData.value.status === 'RUNNING');

  const statusInfo = computed(() => {
    const status = getNodeDisplayStatus(nodeData.value);
    return {
      ...STATUS_ICON_MAP[status],
      text: NODE_STATUS_META[status].text,
    };
  });

  const { isActive, pause, resume } = useTimeoutPoll(pollNewLogs, 5000);
  const { isFullscreen, toggle } = useFullscreen(logContentRef);
  // 处理节点状态已完成，但剩余日志还没来的及刷新到日志接口的情况，请求多一次，确保拿到完整日志
  const { start: startFinalLogRequest } = useTimeoutFn(pollNewLogs, 5000, { immediate: false });

  watch(
    () => isRunning.value,
    (isRunning) => {
      if (isRunning && !isActive.value) {
        resume();
      }
      if (!isRunning && isActive.value) {
        pause();
        startFinalLogRequest();
      }
    },
  );

  watch(
    () => props.isShow,
    async (isShow) => {
      if (isShow) {
        // 侧滑打开时内容才挂载，等这一轮渲染结束日志容器才存在
        await nextTick();
        dbLogRef.value?.init();
        return;
      }
      // 关闭侧滑时中断在途分片并清空，避免下次打开残留旧结果
      pause();
      resetLogState();
    },
    {
      immediate: true,
    },
  );

  watch(isFullscreen, async () => {
    dbLogRef.value?.destroy();
    await nextTick();
    dbLogRef.value?.init();
    dbLogRef.value?.setLog(logState.data);
  });

  const getLogContent = () => {
    const messageList = dbLogRef.value!.getValue();
    return messageList.join('\n');
  };

  const handleChangeDate = (data: ServiceReturnType<typeof getRetryNodeHistories>[number]) => {
    if (logState.loading) {
      return;
    }
    currentData.value = data;
    emits('versionChange', data.version);
    pause();
    resetLogState();
    getNodeLogRequest(true);
  };

  const handleCopyLog = () => {
    if (logState.loading) {
      return;
    }
    const content = getLogContent();
    execCopy(content);
  };

  const handleDownLoaderLog = () => {
    if (logState.loading) {
      return;
    }
    const content = getLogContent();
    downloadText(`${nodeData.value.id}.log`, content);
  };

  onBeforeUnmount(() => {
    // 组件卸载后在途分片的返回不再写入
    logToken += 1;
  });
</script>

<style lang="less" scoped>
  .log-content {
    width: 100%;
    height: 100%;

    .log-tools {
      display: flex;
      align-items: center;
      width: 100%;
      height: 42px;
      padding: 0 16px;
      line-height: 42px;
      background: #202024;

      .log-tools-title {
        display: flex;
        align-items: center;

        .main-title {
          margin-left: 6px;
          font-size: 14px;
          color: #c4c6cc;
        }

        .tip {
          margin-left: 4px;
          font-size: 12px;
          color: #979ba5;
        }
      }

      .log-tools-bar {
        flex: 1;
        justify-content: flex-end;
        display: flex;
        align-items: center;

        i {
          margin-left: 16px;
          font-size: 16px;
          cursor: pointer;
        }

        // 加载中：工具栏禁用（点击守卫在事件回调里提前 return）
        &.is-loading {
          i,
          .execute-history {
            cursor: not-allowed;
          }
        }
      }
    }
  }
</style>
