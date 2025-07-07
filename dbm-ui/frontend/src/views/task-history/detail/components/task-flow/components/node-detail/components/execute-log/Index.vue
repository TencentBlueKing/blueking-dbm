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
      :style="{ height: isFullscreen ? 'calc(100% - 42px)' : '100%' }" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getNodeLog, getRetryNodeHistories } from '@services/source/taskflow';

  import DbLog from '@components/db-log/index.vue';

  import { downloadText, execCopy } from '@utils';

  import { useFullscreen, useTimeoutPoll } from '@vueuse/core';

  import { type Node } from '../../../flow-canvas/utils';

  import ExecuteHistory from './components/ExecuteHistory.vue';

  type NodeLog = ServiceReturnType<typeof getNodeLog>[number];

  interface Props {
    node?: Node;
    rootId?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    node: () => ({}) as NonNullable<Props['node']>,
    rootId: '',
  });

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
      root_id: props.rootId,
      version_id: currentData.value.version,
    };
    getNodeLog(params)
      .then((data) => {
        logState.data = data;
        handleClearLog();
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

  const dbLogRef = ref<InstanceType<typeof DbLog>>();
  const logContentRef = ref<HTMLDivElement>();
  const currentData = ref({ version: '' });

  const logState = reactive({
    data: [] as NodeLog[],
    loading: false,
  });

  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'un-full-screen' : 'full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));
  const nodeData = computed(() => props.node || {});

  const isRunning = computed(() => nodeData.value.status === 'RUNNING');

  const statusInfo = computed(() => {
    const info = {
      color: '',
      icon: '',
      text: '',
    };

    if (nodeData.value.todoId && nodeData.value.status !== 'FAILED') {
      info.text = t('待继续');
      info.color = '#F59500';
      info.icon = 'dengdaiqueren';
      return info;
    }

    switch (nodeData.value.status) {
      case 'RUNNING':
        info.text = t('执行中');
        info.color = '#979BA5';
        info.icon = 'loading';
        break;
      case 'FINISHED':
        info.text = t('执行成功');
        info.color = '#2CAF5E';
        info.icon = 'check';
        break;
      case 'FAILED':
        info.text = t('执行失败');
        info.color = '#EA3636';
        info.icon = 'delete-fill';
        break;
      default:
        info.text = t('待执行');
        info.color = '#979BA5';
        info.icon = 'waiting-shalou';
        break;
    }

    return info;
  });

  const { isActive, pause, resume } = useTimeoutPoll(getNodeLogRequest, 5000);
  const { isFullscreen, toggle } = useFullscreen(logContentRef);

  watch(
    () => isRunning.value,
    (isRunning) => {
      if (isRunning && !isActive.value) {
        resume();
      }
      if (!isRunning && isActive.value) {
        pause();
      }
    },
  );

  watch(
    isShow,
    () => {
      if (isShow.value) {
        setTimeout(() => {
          dbLogRef.value?.init();
        });
      }
    },
    {
      immediate: true,
    },
  );

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

  const handleDownLoaderLog = () => {
    const messageList = dbLogRef.value!.getValue();
    downloadText(`${nodeData.value.id}.log`, messageList.join('\n'));
  };

  const handleChangeDate = (data: ServiceReturnType<typeof getRetryNodeHistories>[number]) => {
    currentData.value = data;
    pause();
    setTimeout(() => {
      handleClearLog();
      getNodeLogRequest(true);
    });
  };

  const handleCopyLog = () => {
    const messageList = dbLogRef.value!.getValue();
    execCopy(messageList.join('\n'));
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .log-content {
    width: 100%;
    height: 100%;

    .log-tools {
      .flex-center();

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
        .flex-center();

        i {
          margin-left: 16px;
          font-size: 16px;
          cursor: pointer;
        }
      }
    }
  }
</style>
