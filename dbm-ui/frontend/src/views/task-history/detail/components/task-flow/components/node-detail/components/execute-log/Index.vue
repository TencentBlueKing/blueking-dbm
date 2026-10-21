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
      <div class="log-tools-bar">
        <ExecuteHistory
          v-if="isShow"
          :node-id="nodeData.id"
          :root-id="rootId"
          @change="handleChangeDate" />
        <DbIcon
          v-bk-tooltips="t('复制')"
          type="copy"
          @click="handleCopyLog" />
        <a
          v-bk-tooltips="t('下载')"
          :download="`${nodeData.id}.log`"
          :href="exportLogUrl">
          <DbIcon type="import" />
        </a>
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
      :style="{ height: tooLarge ? 'calc(100% - 42px)' : 'calc(100% - 42px)' }" />
    <!-- <div
      v-if="tooLarge"
      class="log-export-tip">
      {{ t('日志过大，页面仅展示部分内容，更多内容请下载') }}
      <a
        :download="`${nodeData.id}.log`"
        :href="exportLogUrl">
        {{ t('完整日志') }}
      </a>
    </div> -->
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getNodeLogV2, getRetryNodeHistories } from '@services/source/taskflow';

  import DbLog from '@components/db-log/index.vue';

  import {
    type FlowNode,
    getNodeDisplayStatus,
    NODE_STATUS_META,
    type NodeDisplayStatus,
  } from '@views/task-history/detail/utils';

  import { execCopy } from '@utils';

  import { useFullscreen, useTimeoutFn, useTimeoutPoll } from '@vueuse/core';

  import ExecuteHistory from './components/ExecuteHistory.vue';

  type NodeLog = ServiceReturnType<typeof getNodeLogV2>['result'][number];

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

  // node_log_v2 接口带 download=true，返回完整日志附件，浏览器直接保存
  const exportLogUrl = computed(() => {
    const params = new URLSearchParams({
      node_id: nodeData.value.id,
      version_id: currentData.value.version,
    });
    return `/apis/taskflow/${props.rootId}/node_log_v2/?${params.toString()}&download=true`;
  });

  // 增量游标：执行中轮询时回传给 v2 接口，只返回 cursor 之后的新日志
  const logCursor = ref('');

  const getNodeLogRequest = (isInit?: boolean) => {
    if (!currentData.value.version) {
      return;
    }

    // 执行中轮询且回执过 cursor 时走增量请求；首次加载 / 切换版本走全量
    const isIncremental = !isInit && isRunning.value && Boolean(logCursor.value);
    logState.loading = !isIncremental;
    const params = {
      cursor: isIncremental ? logCursor.value : undefined,
      node_id: nodeData.value.id,
      root_id: props.rootId,
      version_id: currentData.value.version,
    };

    return (
      getNodeLogV2(params)
        .then((data) => {
          tooLarge.value = data.too_large;
          if (data.cursor) {
            logCursor.value = data.cursor;
          }
          // 增量响应只含新增条目，直接往后追加
          if (isIncremental) {
            if (data.result.length > 0) {
              logState.data = [...logState.data, ...data.result];
              dbLogRef.value?.appendLog(data.result);
            }
            return;
          }
          logState.data = data.result;
          // 请求可能在组件卸载后才返回
          dbLogRef.value?.setLog(logState.data);
        })
        // 报错提示已由请求层统一给出。这里必须吞掉：useTimeoutPoll 的回调一旦抛错，轮询就再也不会续上
        .catch(() => {})
        .finally(() => {
          logState.loading = false;
          if (isInit && nodeData.value.status === 'RUNNING' && !isActive.value) {
            resume();
          }
        })
    );
  };

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
    data: [] as NodeLog[],
    loading: false,
  });
  // 后端标记日志过大（页面仅展示部分），用于追加导出提示行
  const tooLarge = ref(false);

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

  const { isActive, pause, resume } = useTimeoutPoll(getNodeLogRequest, 5000);
  const { isFullscreen, toggle } = useFullscreen(logContentRef);
  // 处理节点状态已完成，但剩余日志还没来的及刷新到日志接口的情况，请求多一次，确保拿到完整日志
  const { start: startFinalLogRequest } = useTimeoutFn(getNodeLogRequest, 5000, { immediate: false });

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
    async () => {
      if (props.isShow) {
        // 侧滑打开时内容才挂载，等这一轮渲染结束日志容器才存在
        await nextTick();
        dbLogRef.value?.init();
      }
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
    currentData.value = data;
    emits('versionChange', data.version);
    pause();
    // 切换版本后旧游标失效，重置为全量拉取
    logCursor.value = '';
    getNodeLogRequest(true);
  };

  const handleCopyLog = () => {
    const content = getLogContent();
    execCopy(content);
  };
</script>

<style lang="less" scoped>
  .log-content {
    width: 100%;
    height: 100%;

    .log-export-tip {
      display: flex;
      height: 28px;
      padding: 0 16px;
      font-size: 12px;
      color: #ff9c01;
      background: #3f3223;
      align-items: center;

      a {
        margin-left: 4px;
        color: #3a84ff;
        cursor: pointer;
      }
    }

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

        a {
          display: inline-flex;
          margin-left: 16px;
          color: inherit;
          align-items: center;

          i {
            margin-left: 0;
          }
        }

        > i {
          margin-left: 16px;
          font-size: 16px;
          cursor: pointer;
        }
      }
    }
  }
</style>
