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
    v-model:is-show="state.isShow"
    class="log"
    quick-close
    render-directive="if"
    :width="960"
    @hidden="handleClose">
    <template #header>
      <div class="log-header">
        <div class="log-header-left">
          <span
            v-overflow-tips="{ content: `【${nodeData.name}】 ${t('日志详情')}`, theme: 'light' }"
            class="log-header__title text-overflow">
            {{ `【${nodeData.name}】 ${t('日志详情')}` }}
          </span>
          <div class="log-header__info">
            <RetrySelector
              :node-id="nodeData.id"
              @change="handleChangeDate" />
            <BkTag
              class="ml-16 mr-16"
              :theme="status.theme">
              {{ status.text }}
            </BkTag>
            <span>
              {{ $t('总耗时') }}
              <CostTimer
                :is-timing="STATUS_RUNNING"
                :value="costTime" />
            </span>
          </div>
        </div>
        <div
          v-if="STATUS_FAILED && nodeData.retryable"
          class="log-header__btn">
          <BkPopover
            v-model:is-show="refreshShow"
            theme="light"
            trigger="manual"
            :z-index="99999">
            <BkButton
              class="refresh-btn"
              @click="() => refreshShow = true">
              <i class="db-icon-refresh mr5" />{{ $t('失败重试') }}
            </BkButton>
            <template #content>
              <div class="tips-content">
                <div class="title">
                  {{ $t('确定重试吗') }}
                </div>
                <div class="btn">
                  <span
                    class="bk-button-primary bk-button mr-8"
                    @click="handleRefresh">{{ $t('确定') }}</span>
                  <span
                    class="bk-button"
                    @click="() => refreshShow = false">{{ $t('取消') }}</span>
                </div>
              </div>
            </template>
          </BkPopover>
        </div>
      </div>
    </template>
    <template #default>
      <div
        ref="logContentRef"
        class="log-content">
        <div class="log-tools">
          <span class="log-tools__title">{{ $t('执行日志') }} <span> {{ $t('日志保留7天_如需要请下载保存') }}</span></span>
          <div class="log-tools__bar">
            <i
              v-bk-tooltips="$t('复制')"
              class="db-icon-copy"
              @click="handleCopyLog" />
            <i
              v-bk-tooltips="$t('下载')"
              class="db-icon-import"
              @click="handleDownLoaderLog" />
            <i
              v-bk-tooltips="screenIcon.text"
              :class="screenIcon.icon"
              @click="toggle" />
          </div>
        </div>
        <div class="log-details">
          <BkLog ref="logRef" />
        </div>
      </div>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { format } from 'date-fns';
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getNodeLog } from '@services/taskflow';
  import type { NodeLog, RetryNodeItem } from '@services/types/taskflow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import BkLog from '@components/vue2/bk-log/index.vue';

  import { useFullscreen, useTimeoutPoll } from '@vueuse/core';

  import { NODE_STATUS_TEXT } from '../common/graphRender';
  import type { GraphNode } from '../common/utils';

  import RetrySelector from './RetrySelector.vue';

  import { useCopy } from '@/hooks';


  const props = defineProps({
    isShow: {
      type: Boolean,
      default: false,
    },
    node: {
      type: Object as PropType<GraphNode>,
      default: () => ({}),
    },
  });

  const emit = defineEmits(['close', 'refresh']);

  const { t } = useI18n();
  const copy = useCopy();

  const route = useRoute();
  const rootId = computed(() => route.params.root_id as string);
  const state = reactive({
    isShow: false,
  });
  const nodeData = computed(() => props.node.data || {});
  const status = computed(() => {
    const themes = {
      FINISHED: 'success',
      RUNNING: 'info',
      FAILED: 'danger',
      REVOKED: 'danger',
      READY: undefined,
      CREATED: undefined,
    } as Record<string, string|undefined>;
    const status = nodeData.value.status ? nodeData.value.status : 'READY';

    return {
      text: NODE_STATUS_TEXT[status],
      theme: themes[status],
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

  const formatLogData = (data: NodeLog[] = []) => {
    const regex = /^##\[[a-z]+]/;

    return data.map((item) => {
      const { timestamp, message, levelname } = item;
      const time = format(new Date(Number(timestamp)), 'yyyy-MM-dd HH:mm:ss');
      return {
        ...item,
        message: regex.test(message)
          ? message.replace(regex, (match: string) => `${match}[${time} ${levelname}]`)
          : `[${time} ${levelname}] ${message}`,
      };
    });
  };

  /** 获取日志及下载日志接口  */
  const getNodeLogRequest = (isInit?: boolean) => {
    if (!currentData.value.version) return;

    const params: any = {
      root_id: rootId.value,
      node_id: nodeData.value.id,
      version_id: currentData.value.version,
    };
    getNodeLog(params)
      .then((res) => {
        logState.data = res;
        handleClearLog();
        handleSetLog(formatLogData(res));
      })
      .finally(() => {
        logState.loading = false;
        isInit && nodeData.value.status === 'RUNNING' && !isActive.value && resume();
      });
  };

  const { isActive, pause, resume } = useTimeoutPoll(getNodeLogRequest, 5000);

  watch(() => STATUS_RUNNING.value, (val) => {
    val && !isActive.value && resume();
    !val && isActive.value && pause();
  });

  watch(() => props.isShow, () => {
    state.isShow = props.isShow;
  }, { immediate: true });

  /**
   * 日志全屏切换
   */
  const logContentRef = ref<HTMLDivElement>();
  const { isFullscreen, toggle } = useFullscreen(logContentRef);
  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  const logRef = ref();
  const logState = reactive({
    data: [] as NodeLog[],
    loading: false,
  });

  /**
   * 清空日志
   */
  const handleClearLog = () => {
    logRef.value.handleLogClear();
  };

  /**
   * 设置日志
   */
  const handleSetLog = (data: NodeLog[] = []) => {
    logRef.value.handleLogAdd(data);
  };

  /** 当前选中日志版本的信息 */
  const currentData = ref({ version: '' });
  /**
   * 下载日志
   */
  const handleDownLoaderLog = () => {
    const params: any = {
      root_id: rootId.value,
      node_id: nodeData.value.id,
      version_id: currentData.value.version,
    };
    const url = `/apis/taskflow/${params.root_id}/node_log/?root_id=${params.root_id}&node_id=${params.node_id}&version_id=${params.version_id}&download=1`;
    const elt = document.createElement('a');
    elt.setAttribute('href', url);
    elt.style.display = 'none';
    document.body.appendChild(elt);
    elt.click();
    document.body.removeChild(elt);
  };
  /**
   * 切换日志版本
   */
  const handleChangeDate = (data: RetryNodeItem) => {
    currentData.value = data;
    pause();
    nextTick(() => {
      logState.loading = true;
      handleClearLog();
      getNodeLogRequest(true);
    });
  };
  const handleCopyLog = () => {
    const logData = formatLogData(logState.data);
    copy(logData.map(item => item.message).join('\n'));
  };

  const handleRefresh = () => {
    emit('refresh', { data: nodeData.value });
    refreshShow.value = false;
  };

  const refreshShow = ref(false);
  /**
   * close slider
   */
  const handleClose = () => {
    emit('close');
    pause();
  };

</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

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

  .log {
    &-header {
      width: 100%;
      .flex-center();

      &-left {
        flex: 1;
        width: 0;
        padding-right: 8px;
        .flex-center();
      }

      &__info {
        padding-left: 4px;
        font-size: @font-size-normal;
        font-weight: normal;
        flex-shrink: 0;
        .flex-center();
      }

      &__btn {
        padding-right: 13px;
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
    }

    :deep(.bk-modal-content) {
      height: 100%;
      max-height: calc(100% - 60px) !important;
      padding: 16px;
    }

    :deep(.bk-modal-footer) {
      display: none;
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

    &__title {
      font-size: 14px;
      color: white;

      span {
        display: inline-block;
        margin-left: 5px;
        color: #c4c6cc;
      }
    }

    &__bar {
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
    height: calc(100% - 42px);
  }
</style>
