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
    v-show="skippState.isShow"
    ref="skippTipsRef"
    class="mission-tips-content">
    <div class="title">
      {{ $t('确定忽略错误吗') }}
    </div>
    <div class="btn">
      <span
        class="bk-button-primary bk-button mr-8"
        @click.stop="handleSkippClick">{{ $t('确定') }}</span>
      <span
        class="bk-button"
        @click.stop="handleSkippCancel">{{ $t('取消') }}</span>
    </div>
  </div>
  <div
    v-show="refreshState.isShow"
    ref="refreshTemplateRef"
    class="mission-tips-content">
    <div class="title">
      {{ $t('确定重试吗') }}
    </div>
    <div class="btn">
      <span
        class="bk-button-primary bk-button mr-8"
        @click.stop="handleRefreshClick">{{ $t('确定') }}</span>
      <span
        class="bk-button"
        @click.stop="handleRefreshCancel">{{ $t('取消') }}</span>
    </div>
  </div>
  <MainBreadcrumbs class="custom-main-breadcrumbs">
    <template #append>
      <div
        v-if="statusText"
        class="status-info">
        <span class="mr-8">{{ $t('状态') }}: </span>
        <span>
          <BkTag :theme="getStatusTheme(true)">{{ statusText }}</BkTag>
        </span>
      </div>
      <div class="status-info">
        <span class="mr-8">{{ $t('总耗时') }}: </span>
        <CostTimer
          :is-timing="flowState.details?.flow_info?.status === 'RUNNING'"
          :value="(flowState.details?.flow_info?.cost_time || 0)" />
      </div>
      <BkPopover
        v-if="isShowRevokePipelineButton"
        v-model:is-show="isShowRevokePipelineTips"
        boundary="parent"
        theme="light"
        trigger="manual">
        <BkButton
          ref="revokeButtonRef"
          class="status-stop-button"
          :loading="isRevokePipeline"
          @click="handleToggleRevokeTips">
          <DbIcon type="revoke" />
          {{ $t('终止任务') }}
        </BkButton>
        <template #content>
          <div
            v-clickoutside:[revokeButtonRef?.$el]="handleHiddenRevokeTips"
            class="mission-tips-content">
            <div class="title">
              {{ $t('确定终止任务吗') }}
            </div>
            <div class="btn">
              <BkButton
                class="mr-8"
                :loading="isRevokePipeline"
                theme="primary"
                @click.stop="handleRevokePipeline">
                {{ $t('确定') }}
              </BkButton>
              <BkButton @click="handleHiddenRevokeTips">
                {{ $t('取消') }}
              </BkButton>
            </div>
          </div>
        </template>
      </BkPopover>
    </template>
  </MainBreadcrumbs>
  <div class="mission-details">
    <BkLoading
      :loading="flowState.loading"
      style="height: 100%;">
      <DbCard
        mode="collapse"
        :title="$t('基本信息')">
        <EditInfo
          class="mission-details__base"
          :columns="baseColumns"
          :data="baseInfo"
          readonly
          width="25%" />
      </DbCard>
      <DbCard
        ref="flowTopoRef"
        class="mission-details__flows"
        :mode="cardMode"
        :title="$t('任务流程')">
        <template #header-right>
          <div
            class="flow-tools"
            @click.stop>
            <i
              v-bk-tooltips="$t('放大')"
              class="flow-tools__icon db-icon-plus-circle"
              @click.stop="handleZoomIn" />
            <i
              v-bk-tooltips="$t('缩小')"
              class="flow-tools__icon db-icon-minus-circle"
              @click.stop="handleZoomOut" />
            <i
              v-bk-tooltips="$t('还原')"
              class="flow-tools__icon db-icon-position"
              @click.stop="handleZoomReset" />
            <BkPopover
              v-model:is-show="flowState.minimap.isShow"
              boundary="parent"
              :offset="{
                mainAxis: 12,
                crossAxis: 48,
              }"
              placement="bottom-end"
              theme="light mission-minimap-popover"
              trigger="manual"
              :z-index="9999"
              @click.stop>
              <DbIcon
                ref="minimapTriggerRef"
                v-bk-tooltips="$t('缩略图')"
                class="flow-tools__icon"
                :class="{ 'flow-tools__icon--active': flowState.minimap.isShow }"
                type="minimap"
                @click.stop="handleShowMinimap" />
              <template #content>
                <Minimap
                  ref="minimapRef"
                  v-clickoutside:[minimapTriggerRef?.$el]="handleHiddenMinimap"
                  style="background-color: rgb(245 247 251);"
                  @change="handleTranslate" />
              </template>
            </BkPopover>
            <i
              v-bk-tooltips="screenIcon.text"
              class="flow-tools__icon"
              :class="[screenIcon.icon]"
              @click.stop="toggle" />
            <BkPopover
              v-model:is-show="isShowHotKey"
              boundary="parent"
              placement="bottom"
              theme="light"
              trigger="manual"
              :z-index="9999"
              @click.stop>
              <DbIcon
                ref="hotKeyTriggerRef"
                v-bk-tooltips="$t('快捷键')"
                class="flow-tools__icon"
                :class="{ 'flow-tools__icon--active': isShowHotKey }"
                type="keyboard"
                @click.stop="handleShowHotKey" />
              <template #content>
                <div
                  v-clickoutside:[hotKeyTriggerRef?.$el]="handleHiddenHotKey"
                  class="hot-key">
                  <div class="hot-key-title">
                    {{ $t('快捷键') }}
                  </div>
                  <div class="hot-key-list">
                    <div class="hot-key-item">
                      <span class="hot-key-text">{{ $t('放大') }}</span>
                      <span class="hot-key-code">Ctrl</span>
                      <span class="hot-key-code">+</span>
                    </div>
                    <div class="hot-key-item">
                      <span class="hot-key-text">{{ $t('缩小') }}</span>
                      <span class="hot-key-code">Ctrl</span>
                      <span class="hot-key-code">-</span>
                    </div>
                    <div class="hot-key-item">
                      <span class="hot-key-text">{{ $t('还原') }}</span>
                      <span class="hot-key-code">Ctrl</span>
                      <span class="hot-key-code">0</span>
                    </div>
                  </div>
                </div>
              </template>
            </BkPopover>
          </div>
        </template>
        <div
          :id="flowState.flowSelectorId"
          ref="flowRef"
          class="mission-flows"
          @click="handleHiddenTips" />
      </DbCard>
    </BkLoading>
  </div>
  <NodeLog
    :is-show="logState.isShow"
    :node="logState.node"
    @close="() => logState.isShow = false"
    @refresh="handleRefresh" />
  <!-- 结果文件功能 -->
  <RedisResultFiles
    :id="rootId"
    v-model:is-show="isShowResultFile" />
  <!-- 主机预览 -->
  <HostPreview
    v-model:is-show="showHostPreview"
    :biz-id="baseInfo.bk_biz_id"
    :host-ids="baseInfo.bk_host_ids || []" />
</template>

<script setup lang="tsx">
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { getTaskflowDetails, retryTaskflowNode, revokePipeline, skipTaskflowNode } from '@services/taskflow';
  import type { FlowsData } from '@services/types/taskflow';

  import { useMainViewStore } from '@stores';

  import { dbTippy } from '@common/tippy';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';
  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';
  import Minimap from '@components/minimap/Minimap.vue';

  import { generateId, getCostTimeDisplay, messageSuccess } from '@utils';

  import { useFullscreen, useTimeoutPoll } from '@vueuse/core';

  import {
    STATUS,
    type STATUS_STRING,
  } from '../common/const';
  import GraphCanvas from '../common/graphCanvas';
  import {
    formatGraphData,
    type GraphLine,
    type GraphNode,
  } from '../common/utils';
  import NodeLog from '../components/NodeLog.vue';
  import HostPreview from '../components/PreviewHost.vue';
  import RedisResultFiles from '../components/RedisResultFiles.vue';

  import { TicketTypes, type TicketTypesStrings } from '@/common/const';

  /**
   * 设置自定义面包屑
   */
  const mainViewStore = useMainViewStore();
  nextTick(() => {
    mainViewStore.$patch({
      customBreadcrumbs: true,
      hasPadding: false,
    });
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const currentScope = getCurrentScope();
  const rootId = computed(() => route.params.root_id as string);
  const refreshTemplateRef = ref<HTMLDivElement>();
  const skippTipsRef = ref<HTMLDivElement>();
  const flowRef = ref<HTMLDivElement>();
  const minimapRef = ref();
  const minimapTriggerRef = ref();
  const isShowHotKey = ref(false);
  const hotKeyTriggerRef = ref();
  const revokeButtonRef = ref();
  const isRevokePipeline = ref(false);
  const isShowRevokePipelineTips = ref(false);
  const showHostPreview = ref(false);
  const isShowRevokePipelineButton = computed(() => !['REVOKED', 'FAILED', 'FINISHED'].includes(flowState.details?.flow_info?.status));

  const isShowResultFile = ref(false);
  const flowState = reactive({
    flowSelectorId: generateId('mission_flow_'),
    details: {} as FlowsData,
    flowData: {
      locations: [] as GraphNode[],
      lines: [] as GraphLine[],
    },
    loading: false,
    instance: null as any,
    minimap: {
      width: 380,
      height: 160,
      windowWidth: 0,
      windowHeight: 0,
      viewportWidth: 210,
      viewportHeight: 110,
      isShow: false,
    },
  });
  const expandNodes: string[] = [];
  const baseInfo = computed(() => flowState.details.flow_info || {});
  const statusText = computed(() => {
    const value = baseInfo.value.status as STATUS_STRING;
    return value && STATUS[value] ? t(STATUS[value]) : '';
  });

  const getStatusTheme = (isTag = false) => {
    const value = baseInfo.value.status;
    if (isTag && value === 'RUNNING') return 'info';
    const themes = {
      RUNNING: 'loading',
      CREATED: 'default',
      FINISHED: 'success',
    };
    return themes[value as keyof typeof themes] || 'danger';
  };

  const showResultFileTypes: TicketTypesStrings[] = [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE];
  const baseColumns = computed(() => {
    const columns: InfoColumn[][] = [
      [{
        label: t('任务ID'),
        key: 'root_id',
        isCopy: true,
      }, {
        label: t('任务类型'),
        key: 'ticket_type_display',
      }],
      [{
        label: t('开始时间'),
        key: 'created_at',
      }, {
        label: t('结束时间'),
        key: 'updated_at',
      }],
      [{
        label: t('状态'),
        key: '',
        render: () => <DbStatus style="vertical-align: top;" type="linear" theme={getStatusTheme()}>
        <span>{statusText.value || '--'}</span>
      </DbStatus>,
      }, {
        label: t('耗时'),
        key: '',
        render: () => getCostTimeDisplay(baseInfo.value.cost_time) as string,
      }],
      [{
        label: t('执行人'),
        key: 'created_by',
      }, {
        label: t('关联单据'),
        key: 'uid',
        render: () => {
          const { uid } = baseInfo.value;
          return (
            <bk-button text theme="primary" onClick={handleToTicket.bind(null, uid)}>{ uid }</bk-button>
          );
        },
      }],
    ];

    // 结果文件
    if (showResultFileTypes.includes(baseInfo.value.ticket_type) && baseInfo.value.status === 'FINISHED') {
      columns[0].push({
        label: t('结果文件'),
        key: '',
        render: () => <bk-button text theme="primary" onClick={handleShowResultFile}>{t('查看结果文件')}</bk-button>,
      });
    }

    // 预览主机
    const hostNums = baseInfo.value.bk_host_ids?.length ?? 0;
    if (hostNums > 0) {
      columns[0].push({
        label: t('涉及主机'),
        key: 'hosts',
        render: () => (
          <bk-button class="pl-4 pr-4" theme="primary" text onClick={handleShowHostPreview}>{hostNums}</bk-button>
        ),
      });
    }
    return columns;
  });
  const tippyInstances = ref<Instance[]>();
  const skippInstances = ref<Instance[]>();
  const updateMinimap = () => {
    const el = flowRef.value?.querySelector('.canvas-wrapper');
    if (el) {
      const { windowWidth, windowHeight } = flowState.minimap;
      minimapRef.value.updateCanvas(el, {
        width: windowWidth,
        height: windowHeight,
        style: {
          transform: 'translate(60px, 100px) scale(1) rotate(0deg)',
        },
      });
    }
  };

  const handleShowResultFile = () => {
    isShowResultFile.value = true;
  };

  const handleShowHostPreview = () => {
    showHostPreview.value = true;
  };

  /**
   * 跳转到关联单据
   */
  const handleToTicket = (id: string) => {
    const url = router.resolve({
      name: 'SelfServiceMyTickets',
      query: { filterId: id },
    });
    window.open(url.href, '_blank');
  };

  /**
   * 渲染画布节点
   */
  const renderNodes = (updateLogData = false) => {
    const { locations, lines } = formatGraphData(flowState.details, expandNodes);
    flowState.instance.update({
      locations,
      lines,
    });
    flowState.minimap.windowWidth = Math.max(...locations.map(item => item.x || 0)) + 400;
    flowState.minimap.windowHeight = Math.max(...locations.map(item => item.y || 0)) + 400;
    // 如果打开侧栏需要更新侧栏的节点状态
    if (updateLogData && logState.isShow) {
      const node = locations.find(item => item.id === logState.node.id);
      if (node) {
        logState.node = node;
      }
    }
  };

  /**
   * 获取任务详情数据
   */
  const fetchTaskflowDetails = (loading = false) => {
    flowState.loading = loading;
    getTaskflowDetails(rootId.value as string)
      .then((res) => {
        flowState.details = res;
        // 渲染失败重试tips
        flowState.instance.setUpdateCallback(() => {
          setTimeout(() => {
            tippyInstances.value?.forEach?.(t => t.destroy());
            tippyInstances.value = dbTippy(document.querySelectorAll('.operation-icon.db-icon-refresh-2'), {
              content: t('失败重试'),
            });
            skippInstances.value?.forEach?.(t => t.destroy());
            skippInstances.value = dbTippy(document.querySelectorAll('.operation-icon.db-icon-stop'), {
              content: t('忽略错误'),
            });
          }, 30);
        });
        // 渲染画布节点
        renderNodes(true);
        // 设置面包屑内容
        mainViewStore.breadCrumbsTitle = `${res.flow_info.ticket_type_display}【${res.flow_info.root_id}】`;
      })
      .finally(() => {
        flowState.loading = false;
        // 启动轮询
        if (currentScope?.active) {
          isActive.value === false && resume();
        } else {
          pause();
        }
      });
  };
  const { isActive, pause, resume } = useTimeoutPoll(fetchTaskflowDetails, 10000);

  /**
   * 拓扑全屏切换
   */
  const flowTopoRef = ref<HTMLDivElement>();
  const { isFullscreen, toggle } = useFullscreen(flowTopoRef);
  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));
  const cardMode = computed(() => (isFullscreen.value ? 'normal' : 'collapse'));

  /**
   * 重试节点
   */
  const handleRefresh = (node: GraphNode) => {
    retryTaskflowNode({
      root_id: rootId.value as string,
      node_id: node.data.id,
    }).then(() => {
      // eslint-disable-next-line no-param-reassign
      node.data.status = 'RUNNING';
      renderNodes();
      fetchTaskflowDetails();
    });
  };

  /**
   * 跳过节点
   */
  const handleSkipp = (node: GraphNode) => {
    skipTaskflowNode({
      root_id: rootId.value as string,
      node_id: node.data.id,
    }).then(() => {
      // eslint-disable-next-line no-param-reassign
      node.data.status = 'SKIPPED';
      renderNodes();
      fetchTaskflowDetails();
    });
  };

  const handleRevokePipeline = () => {
    isRevokePipeline.value = true;
    revokePipeline(rootId.value)
      .then(() => {
        fetchTaskflowDetails();
        messageSuccess(t('终止任务成功'));
        isShowRevokePipelineTips.value = false;
      })
      .finally(() => {
        isRevokePipeline.value = false;
      });
  };

  const handleToggleRevokeTips = () => {
    isShowRevokePipelineTips.value = !isShowRevokePipelineTips.value;
  };

  const handleHiddenRevokeTips = () => {
    isShowRevokePipelineTips.value = false;
  };

  /**
   * 查看节点日志
   */
  const logState = reactive({
    isShow: false,
    node: {} as GraphNode,
  });
  const handleShowLog = (node: GraphNode) => {
    logState.isShow = true;
    logState.node = node;
  };
  onUnmounted(() => {
    pause();
    flowState.instance?.destroy();
  });

  const skippState = reactive<{
    instance: Instance | null,
    node: GraphNode | null,
    isShow: boolean,
  }>({
    instance: null,
    node: null,
    isShow: false,
  });

  const refreshState = reactive<{
    instance: Instance | null,
    node: GraphNode | null,
    isShow: boolean,
  }>({
    instance: null,
    node: null,
    isShow: false,
  });

  /**
   * 拓扑操作
   */
  const handleNodeClick = (node: GraphNode, event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    flowState.minimap.isShow = false;
    isShowHotKey.value = false;
    if (event.target) {
      const eventType = (event.target as HTMLElement).getAttribute('data-evt-type');

      if (eventType === 'refresh') {
        refreshState.instance && refreshState.instance.destroy();
        refreshState.instance = dbTippy(event.target as HTMLElement, {
          trigger: 'click',
          theme: 'light',
          content: refreshTemplateRef.value,
          arrow: true,
          placement: 'top',
          appendTo: () => document.body,
          interactive: true,
          allowHTML: true,
          hideOnClick: true,
          maxWidth: 400,
          zIndex: 9999,
        });
        refreshState.instance.show();
        refreshState.node = node;
        refreshState.isShow = true;
        return;
      }

      if (eventType === 'skipp') {
        skippState.instance && skippState.instance.destroy();
        skippState.instance = dbTippy(event.target as HTMLElement, {
          trigger: 'click',
          theme: 'light',
          content: skippTipsRef.value,
          arrow: true,
          placement: 'top',
          appendTo: () => document.body,
          interactive: true,
          allowHTML: true,
          hideOnClick: true,
          maxWidth: 400,
          zIndex: 9999,
        });
        skippState.instance.show();
        skippState.node = node;
        skippState.isShow = true;
        return;
      }

      const targetParent = (event.target as HTMLElement).closest('.node-ractangle');
      const hasLog = targetParent?.getAttribute('data-evt-type') === 'log';
      if (hasLog) {
        handleShowLog(node);
        return;
      }
      /** 展开收起节点 */
      if ((event.target as HTMLElement).className.includes('node-ractangle-collapse-open') || node.children) {
        const expandNodeIndex = expandNodes.findIndex(id => id === node.id);
        if (expandNodeIndex === -1) {
          expandNodes.push(node.id);
        } else {
          expandNodes.splice(expandNodeIndex, 1);
        }
        renderNodes();
        return;
      }
    }
  };

  const handleNodeMouseEnter = (node: GraphNode, event: MouseEvent) => {
    if (event.target) {
      const targetEl = event.target as HTMLElement;
      targetEl.className = `${targetEl.className} mouse-hover`;
    }
  };

  const handleNodeMouseLeave = (node: GraphNode, event: MouseEvent) => {
    if (event.target) {
      const targetEl = event.target as HTMLElement;
      targetEl.className = targetEl.className.replace(' mouse-hover', '');
    }
  };

  const handleZoomReset = () => {
    flowState.instance?.zoomReset();
  };

  const handleZoomIn = () => {
    flowState.instance?.zoomIn();
  };

  const handleZoomOut = () => {
    flowState.instance?.zoomOut();
  };

  /**
   * 取消刷新节点
   */
  const handleRefreshCancel = () => {
    refreshState.instance && refreshState.instance.destroy();
    refreshState.isShow = false;
  };

  /**
   * 确认刷新节点
   */
  const handleRefreshClick = () => {
    if (refreshState.node) {
      handleRefresh(refreshState.node);
    }
    handleRefreshCancel();
  };

  /**
   * 取消跳过节点
   */
  const handleSkippCancel = () => {
    skippState.instance && skippState.instance.destroy();
    skippState.isShow = false;
  };

  /**
   * 确认跳过节点
   */
  const handleSkippClick = () => {
    if (skippState.node) {
      handleSkipp(skippState.node);
    }
    handleSkippCancel();
  };

  const handleTranslate = ({ left, top }: { left: number, top: number }) => {
    if (flowState.instance) {
      const { flowInstance } = flowState.instance;
      // eslint-disable-next-line no-underscore-dangle
      const { x, y } = flowInstance._options.canvasPadding;
      // eslint-disable-next-line no-underscore-dangle
      const { scale } = flowInstance._diagramInstance._canvasTransform;
      const { viewportWidth, viewportHeight } = flowState.minimap;
      const windowWidth = flowState.minimap.windowWidth * scale;
      const windowHeight = flowState.minimap.windowHeight * scale;
      flowState.instance?.translate(
        -(windowWidth * left / viewportWidth) + x,
        -(windowHeight * top / viewportHeight) + y,
      );
    }
  };

  const handleShowMinimap = () => {
    flowState.minimap.isShow = !flowState.minimap.isShow;
    nextTick(() => {
      updateMinimap();
    });
  };

  const handleHiddenMinimap = () => {
    flowState.minimap.isShow = false;
  };

  const handleShowHotKey = () => {
    isShowHotKey.value = !isShowHotKey.value;
  };
  const handleHiddenHotKey = () => {
    isShowHotKey.value = false;
  };

  const handleHiddenTips = () => {
    handleHiddenMinimap();
    handleHiddenHotKey();
  };

  /**
   * 拓扑初始化
   */
  onMounted(() => {
    nextTick(() => {
      flowState.instance = new GraphCanvas(`#${flowState.flowSelectorId}`);
      flowState.instance
        .on('nodeClick', handleNodeClick)
        .on('nodeMouseEnter', handleNodeMouseEnter)
        .on('nodeMouseLeave', handleNodeMouseLeave);
      fetchTaskflowDetails(true);
    });

    document.onkeydown = (e: KeyboardEvent) => {
      const isCtrl = e.ctrlKey || e.metaKey;
      if (isCtrl && e.key === '=') {
        handleZoomIn();
        e.preventDefault();
        return;
      }
      if (isCtrl && e.key === '-') {
        handleZoomOut();
        e.preventDefault();
        return;
      }
      if (isCtrl && e.key === '0') {
        handleZoomReset();
        e.preventDefault();
        return;
      }
    };
  });

</script>

<style lang="less" scoped>
  @import "@styles/mixins";

  :deep(.db-card__content),
  .mission-flows {
    height: 100%;
  }

  .status-info {
    .flex-center();

    margin-right: 24px;
  }

  .status-stop-button {
    padding: 5px 8px;
    border-radius: 50px;

    .db-icon-revoke {
      margin-right: 4px;
    }
  }

  .mission-details {
    height: 100%;
    padding-top: 52px;

    &__base {
      width: 80%;
      padding-left: 40px;

      :deep(.base-info__label) {
        min-width: 100px;
        justify-content: flex-end;
      }
    }

    &__flows {
      height: calc(100% - 150px);
      padding: 14px 0;
      overflow: hidden;
      border-top: 1px solid @border-disable;

      :deep(.db-card__header) {
        padding: 0 24px;
      }

      :deep(.db-card__content) {
        padding-top: 14px;
      }
    }

    .flow-tools {
      padding-bottom: 2px;
      .flex-center();

      &__icon {
        display: block;
        margin-left: 16px;
        font-size: @font-size-large;
        text-align: center;
        cursor: pointer;

        &:hover,
        &--active {
          color: @primary-color;
        }
      }
    }
  }

  .hot-key {
    width: 230px;

    &-title {
      padding-bottom: 8px;
      color: @title-color;
      border-bottom: 1px solid #eaebf0;
    }

    &-item {
      display: flex;
      padding: 8px 0 6px;
      color: @default-color;
      align-items: center;
    }

    &-text {
      margin-right: 32px;
    }

    &-code {
      min-width: 20px;
      padding: 0 6px;
      margin-right: 8px;
      line-height: 18px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
    }
  }
</style>

<style lang="less">
  .mission-tips-content {
    width: 240px;
    padding: 8px 0;
    color: @default-color;

    .btn {
      width: 100%;
      margin-top: 14px;
      text-align: right;

      .bk-button {
        height: 26px;
        padding: 0 12px;
        font-size: 12px;
      }
    }
  }
  .flex() {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .box-shadow(@color: rgba(25,25,41,.1)) {
    box-shadow: 0 2px 4px 0 @color;
  }

  .mission-flows {
    font-size: @font-size-mini;

    .node-round {
      height: 100%;
      padding: 6px;
      font-weight: bold;
      color: @white-color;
      background-color: @bg-white;
      border-radius: 50%;
      .box-shadow();
      .flex();

      span {
        width: 100%;
        line-height: 36px;
        text-align: center;
        background-color: @bg-light-gray;
        border-radius: 50%;
      }

      &--finished {
        span {
          background-color: #4bc7ad;
        }
      }
    }

    .node-hover {
      cursor: pointer;

      &:hover {
        .node-ractangle {
          box-shadow: 0 2px 10px 0 rgb(25 25 41 / 10%);
        }

        .node-ractangle-collapse-open {
          color: @default-color;
        }
      }
    }

    .node-ractangle-layout {
      .flex();

      position: relative;
      height: 100%;

      .node-ractangle-collapse-open {
        color: @gray-color;
        background-color: @bg-white;
        border-radius: 50%;
        flex-shrink: 0;
      }

      .node-ractangle-collapse {
        font-size: 14px;
        cursor: pointer;
        flex-shrink: 0;
      }
    }

    .node-ractangle {
      position: relative;
      width: 100%;
      height: 100%;
      background-color: @bg-white;
      border-radius: 4px;
      flex: 1;
      .box-shadow(rgba(25,25,41,0.05));
      .flex();

      &[data-evt-type="log"] {
        cursor: pointer;
      }

      &__status {
        position: relative;
        flex-shrink: 0;
        width: 48px;
        height: 100%;
        background-color: @bg-light-gray;
        border-radius: 4px 0 0 4px;
        .flex();
      }

      &__icon {
        font-size: 24px;
        color: @white-color;

        &--loading {
          position: absolute;
          top: 50%;
          right: 50%;
          z-index: 0;
          width: 38px;
          height: 38px;
          margin: -19px;
          background-image: url("@images/flow-loading.png");
          background-size: 38px;
          animation: bkdata-ss-draft-node-running 2s linear infinite;

          @keyframes bkdata-ss-draft-node-running {
            from {
              transform: rotate(0deg);
            }

            to {
              transform: rotate(360deg);
            }
          }
        }
      }

      &__content {
        height: 100%;
        padding: 8px;
        overflow: hidden;
        line-height: 16px;
        flex: 1;
        .flex();

        &-left {
          flex: 1;
          overflow: hidden;
        }
      }

      &__text {
        padding-top: 2px;
        color: @gray-color;
      }

      &__operations {
        position: absolute;
        top: -20px;
        left: 0;
        padding-bottom: 10px;

        .operation-icon {
          font-size: 16px;
          color: @white-color;
          cursor: pointer;
          background-color: #929496;
          border-radius: 2px;

          &.db-icon-refresh-2 {
            display: inline-block;
            padding: 1px;
            font-size: 14px;
            vertical-align: top;
          }
        }
      }

      &--finished {
        .node-ractangle__status {
          background-color: #4bc7ad;
        }

        .node-ractangle__text {
          color: #14a568;
        }
      }

      &--running {
        .node-ractangle__status {
          background-color: @bg-primary;
        }

        .node-ractangle__text {
          color: @primary-color;
        }
      }

      &--failed,
      &--revoked {
        .node-ractangle__status {
          background-color: #ff5656;
        }

        .node-ractangle__text {
          color: #ff5656;
        }
      }

      &--skipped {
        .node-ractangle__status {
          background-color: #89c053;
        }

        .node-ractangle__text {
          color: #89c053;
        }
      }
    }

    .bk-graph-node {
      cursor: default !important;

      &.mouse-hover {
        .node-ractangle__operations {
          display: block;
        }
      }
    }
  }

  .mission-minimap-popover {
    padding: 8px !important;
  }
</style>
