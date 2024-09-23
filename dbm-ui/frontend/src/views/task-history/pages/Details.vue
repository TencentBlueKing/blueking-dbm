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
  <div class="mission-detail-page">
    <div
      v-show="skippState.isShow"
      ref="skippTipsRef"
      class="mission-tips-content">
      <div class="title">
        {{ t('确定跳过吗') }}
      </div>
      <div class="btn">
        <span
          class="bk-button-primary bk-button mr-8"
          @click.stop="handleSkippClick">
          {{ t('确定') }}
        </span>
        <span
          class="bk-button"
          @click.stop="handleSkippCancel">
          {{ t('取消') }}
        </span>
      </div>
    </div>
    <div
      v-show="refreshState.isShow"
      ref="refreshTemplateRef"
      class="mission-tips-content">
      <div class="title">
        {{ t('确定重试吗') }}
      </div>
      <div class="btn">
        <span
          class="bk-button-primary bk-button mr-8"
          @click.stop="handleRefreshClick">
          {{ t('确定') }}
        </span>
        <span
          class="bk-button"
          @click.stop="handleRefreshCancel">
          {{ t('取消') }}
        </span>
      </div>
    </div>
    <div
      v-show="todoState.isShow"
      ref="todoTemplateRef"
      class="mission-tips-content">
      <div class="title">
        {{ t('确认继续执行该节点？') }}
      </div>
      <div class="btn">
        <span
          class="bk-button-primary bk-button mr-8"
          @click.stop="handleTodoClick">
          {{ t('确定') }}
        </span>
        <span
          class="bk-button"
          @click.stop="handleTodoCancel">
          {{ t('取消') }}
        </span>
      </div>
    </div>
    <div
      v-show="forceFailState.isShow"
      ref="forceFailTipsRef"
      class="mission-force-fail-tip">
      <div class="title">
        {{ t('确定强制失败吗') }}
      </div>
      <div class="sub-title">将会终止节点运行，并置为强制失败状态</div>
      <div class="btn">
        <span
          class="bk-button-primary bk-button confirm mr-8"
          @click.stop="handleForceFailClick">
          {{ t('强制失败') }}
        </span>
        <span
          class="bk-button"
          @click.stop="handleForceFailCancel">
          {{ t('取消') }}
        </span>
      </div>
    </div>
    <div class="mission-details">
      <BkLoading
        :loading="flowState.loading"
        style="height: 100%">
        <DbCard
          mode="collapse"
          :title="t('基本信息')">
          <EditInfo
            class="mission-details-base"
            :columns="baseColumns"
            :data="baseInfo"
            readonly
            width="25%" />
        </DbCard>
        <DbCard
          ref="flowTopoRef"
          class="mission-details-flows"
          :mode="cardMode"
          :title="t('任务流程')">
          <template #header-right>
            <div
              class="flow-tools"
              @click.stop>
              <PreviewNodeTree
                v-if="todoNodesCount > 0"
                ref="todoToolPreviewNodeTreeRef"
                children="todoChildren"
                margin-right
                :nodes-count="todoNodesCount"
                :nodes-tree-data="todoNodesTreeData"
                status-keypath="待确认n"
                theme="warning"
                title-keypath="人工确认节点（n）"
                :tooltips="t('人工确认节点列表')"
                @after-show="(treeRef: Ref) => handleToolNodeTreeAfterShow(treeRef, false)"
                @node-click="(node: TaskflowList[number], treeRef: Ref) => handleTreeNodeClick(node, treeRef, false)" />
              <PreviewNodeTree
                v-if="flowState.details.flow_info?.status === 'FAILED'"
                ref="failedToolPreviewNodeTreeRef"
                children="failedChildren"
                :nodes-count="failNodesCount"
                :nodes-tree-data="failNodesTreeData"
                status-keypath="失败n"
                title-keypath="失败节点（n）"
                :tooltips="t('失败节点列表')"
                @after-show="(treeRef: Ref) => handleToolNodeTreeAfterShow(treeRef)"
                @node-click="(node: TaskflowList[number], treeRef: Ref) => handleTreeNodeClick(node, treeRef)" />
              <i
                v-bk-tooltips="t('放大')"
                class="flow-tools-icon db-icon-plus-circle"
                @click.stop="handleZoomIn" />
              <i
                v-bk-tooltips="t('缩小')"
                class="flow-tools-icon db-icon-minus-circle"
                @click.stop="handleZoomOut" />
              <i
                v-bk-tooltips="t('还原')"
                class="flow-tools-icon db-icon-position"
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
                  v-bk-tooltips="t('缩略图')"
                  class="flow-tools-icon"
                  :class="{ 'flow-tools-icon-active': flowState.minimap.isShow }"
                  type="minimap"
                  @click.stop="handleShowMinimap" />
                <template #content>
                  <Minimap
                    ref="minimapRef"
                    v-clickoutside:[minimapTriggerRef?.$el]="handleHiddenMinimap"
                    style="background-color: rgb(245 247 251)"
                    @change="handleTranslate" />
                </template>
              </BkPopover>
              <i
                v-bk-tooltips="screenIcon.text"
                class="flow-tools-icon"
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
                  v-bk-tooltips="t('快捷键')"
                  class="flow-tools-icon"
                  :class="{ 'flow-tools-icon-active': isShowHotKey }"
                  type="keyboard"
                  @click.stop="handleShowHotKey" />
                <template #content>
                  <div
                    v-clickoutside:[hotKeyTriggerRef?.$el]="handleHiddenHotKey"
                    class="hot-key">
                    <div class="hot-key-title">
                      {{ t('快捷键') }}
                    </div>
                    <div class="hot-key-list">
                      <div class="hot-key-item">
                        <span class="hot-key-text">{{ t('放大') }}</span>
                        <span class="hot-key-code">Ctrl</span>
                        <span class="hot-key-code">+</span>
                      </div>
                      <div class="hot-key-item">
                        <span class="hot-key-text">{{ t('缩小') }}</span>
                        <span class="hot-key-code">Ctrl</span>
                        <span class="hot-key-code">-</span>
                      </div>
                      <div class="hot-key-item">
                        <span class="hot-key-text">{{ t('还原') }}</span>
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
      :failed-nodes="failLeafNodes"
      :is-show="logState.isShow"
      :node="logState.node"
      @close="() => (logState.isShow = false)"
      @quick-goto="handleQuickGotoFailNodeLog"
      @refresh="handleRefresh" />
    <!-- 结果文件功能 -->
    <RedisResultFiles
      :id="rootId"
      v-model="isShowResultFile" />
    <!-- 主机预览 -->
    <HostPreview
      v-model:is-show="showHostPreview"
      :biz-id="baseInfo.bk_biz_id"
      :host-ids="baseInfo.bk_host_ids || []" />
    <Teleport to="#dbContentTitleAppend">
      <span v-if="flowState.details.flow_info">
        <span> - </span>
        {{ flowState.details.flow_info.ticket_type_display }}【{{ flowState.details.flow_info.root_id }}】
      </span>
    </Teleport>
    <Teleport to="#dbContentHeaderAppend">
      <div class="mission-detail-status-box">
        <div
          v-if="statusText"
          class="mission-detail-status-info">
          <span class="mr-8">{{ t('状态') }}: </span>
          <span>
            <PreviewNodeTree
              v-if="flowState.details.flow_info?.status === 'FAILED'"
              ref="todoTopPreviewNodeTreeRef"
              children="failedChildren"
              :nodes-count="failNodesCount"
              :nodes-tree-data="failNodesTreeData"
              status-keypath="失败n"
              title-keypath="失败节点（n）"
              :tooltips="t('失败节点列表')"
              @after-show="(treeRef: Ref) => handleNodeTreeAfterShow(treeRef)"
              @node-click="(node: TaskflowList[number], treeRef: Ref) => handleTreeNodeClick(node, treeRef)" />
            <PreviewNodeTree
              v-else-if="todoNodesCount > 0"
              ref="failedTopPreviewNodeTreeRef"
              children="todoChildren"
              :nodes-count="todoNodesCount"
              :nodes-tree-data="todoNodesTreeData"
              status-keypath="待确认n"
              theme="warning"
              title-keypath="人工确认节点（n）"
              :tooltips="t('人工确认节点列表')"
              @after-show="(treeRef: Ref) => handleNodeTreeAfterShow(treeRef, false)"
              @node-click="(node: TaskflowList[number], treeRef: Ref) => handleTreeNodeClick(node, treeRef, false)" />
            <BkTag
              v-else
              :theme="getStatusTheme(true)">
              {{ statusText }}
            </BkTag>
          </span>
        </div>
        <div class="mission-detail-status-info">
          <span class="mr-8">{{ t('总耗时') }}: </span>
          <CostTimer
            :is-timing="flowState.details?.flow_info?.status === 'RUNNING'"
            :start-time="utcTimeToSeconds(flowState.details?.flow_info?.created_at)"
            :value="flowState.details?.flow_info?.cost_time || 0" />
        </div>
        <BkPopConfirm
          v-if="todoNodesCount > 0"
          :content="t('确认继续所有人工确认节点')"
          trigger="click"
          width="288"
          @confirm="handleTodoAllPipeline">
          <BkButton
            class="mission-detail-status-operate-button mr-12"
            :loading="isRetryAllPipeline">
            <DbIcon type="check" />
            {{ t('确认继续') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          v-if="isShowFailedPipelineButton"
          :content="t('确定重试所有失败节点')"
          trigger="click"
          width="288"
          @confirm="handleRetryAllPipeline">
          <BkButton
            ref="revokeButtonRef"
            class="mission-detail-status-operate-button mr-12"
            :loading="isRetryAllPipeline">
            <DbIcon type="refresh" />
            {{ t('失败重试') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          v-if="isShowRevokePipelineButton"
          :content="t('确定终止任务吗')"
          trigger="click"
          width="288"
          @confirm="handleRevokePipeline">
          <BkButton
            ref="revokeButtonRef"
            class="mission-detail-status-operate-button"
            :loading="isRevokePipeline">
            <DbIcon type="stop" />
            {{ t('终止任务') }}
          </BkButton>
        </BkPopConfirm>
      </div>
    </Teleport>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import type { Ref } from 'vue'
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import {
    batchRetryNodes,
    forceFailflowNode,
    getTaskflowDetails,
    retryTaskflowNode,
    revokePipeline,
    skipTaskflowNode,
  } from '@services/source/taskflow';
  import { ticketBatchProcessTodo } from '@services/source/ticket'

  import { dbTippy } from '@common/tippy';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  import {
    generateId,
    getCostTimeDisplay,
    messageSuccess,
    utcTimeToSeconds,
  } from '@utils';

  import { useFullscreen, useTimeoutPoll } from '@vueuse/core';

  import GraphCanvas from '../common/graphCanvas';
  import {
    formatGraphData,
    type GraphLine,
    type GraphNode,
  } from '../common/utils';
  import Minimap from '../components/Minimap.vue';
  import NodeLog from '../components/NodeLog.vue';
  import HostPreview from '../components/PreviewHost.vue';
  import PreviewNodeTree from '../components/PreviewNodeTree.vue';
  import RedisResultFiles from '../components/RedisResultFiles.vue';

  import { TicketTypes, type TicketTypesStrings } from '@/common/const';

  type TaskflowDetails = ServiceReturnType<typeof getTaskflowDetails>;
  type TaskflowList = (TaskflowDetails['activities'][string] & {
    failedChildren?: TaskflowDetails['activities'][string][];
    todoChildren?:TaskflowDetails['activities'][string][];
  })[];

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const currentScope = getCurrentScope();

  const refreshTemplateRef = ref<HTMLDivElement>();
  const skippTipsRef = ref<HTMLDivElement>();
  const forceFailTipsRef = ref<HTMLDivElement>();
  const todoTemplateRef = ref<HTMLDivElement>();
  const flowRef = ref<HTMLDivElement>();
  const flowTopoRef = ref<HTMLDivElement>();
  const minimapRef = ref();
  const minimapTriggerRef = ref();
  const isShowHotKey = ref(false);
  const hotKeyTriggerRef = ref();
  const revokeButtonRef = ref();
  const isRetryAllPipeline = ref(false);
  const isRevokePipeline = ref(false);
  const showHostPreview = ref(false);
  const isShowResultFile = ref(false);
  const tippyInstances = ref<Instance[]>([]);
  const skippInstances = ref<Instance[]>([]);
  const forceFailInstances = ref<Instance[]>([]);
  const todoInstances = ref<Instance[]>([])
  const todoNodesTreeData = ref<TaskflowList>([]);
  const failNodesTreeData = ref<TaskflowList>([]);
  const failNodesCount = ref(0);
  const todoTopPreviewNodeTreeRef = ref<InstanceType<typeof PreviewNodeTree>>()
  const failedTopPreviewNodeTreeRef = ref<InstanceType<typeof PreviewNodeTree>>()
  const todoToolPreviewNodeTreeRef = ref<InstanceType<typeof PreviewNodeTree>>()
  const failedToolPreviewNodeTreeRef = ref<InstanceType<typeof PreviewNodeTree>>()
  // const failNodeTreeRef = ref();
  // const topFailNodeTreeRef = ref();
  // const isShowFailNodePanel = ref(false);
  // const isShowTopFailNodePanel = ref(false);

  const failLeafNodes = shallowRef<GraphNode[]>([]);

  const flowState = reactive({
    flowSelectorId: generateId('mission_flow_'),
    details: {} as TaskflowDetails,
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

  const forceFailState = reactive<{
    instance: Instance | null,
    node: GraphNode | null,
    isShow: boolean,
  }>({
    instance: null,
    node: null,
    isShow: false,
  });

  const todoState = reactive<{
    instance: Instance | null,
    node: GraphNode | null,
    isShow: boolean,
  }>({
    instance: null,
    node: null,
    isShow: false,
  });

  /**
   * 查看节点日志
   */
  const logState = reactive({
    isShow: false,
    node: {} as GraphNode,
  });

  let isFindFirstLeafFailNode = false;
  let isFindFirstLeafTodoNode = false;

  const rootId = computed(() => route.params.root_id as string);

  const todoNodesCount = computed(() => {
    if (flowState.details.flow_info) {
      const { status } = flowState.details.flow_info
      return (flowState.details.todos || []).filter(todoItem => (status === 'RUNNING' || status === 'FAILED') && todoItem.status === 'TODO').length
    }
    return 0
  })

  const isShowRevokePipelineButton = computed(() => !['REVOKED', 'FINISHED'].includes(flowState.details?.flow_info?.status));
  const isShowFailedPipelineButton = computed(() => flowState.details?.flow_info?.status === 'FAILED');

  const baseInfo = computed(() => flowState.details.flow_info || {});

  const statusText = computed(() => {
    const statusMap = {
      CREATED: '等待执行',
      READY: '等待执行',
      RUNNING: '执行中',
      SUSPENDED: '执行中',
      BLOCKED: '执行中',
      FINISHED: '执行成功',
      FAILED: '执行失败',
      REVOKED: '已终止',
    };
    const value = baseInfo.value.status as keyof typeof statusMap;
    return value && statusMap[value] ? t(statusMap[value]) : '';
  });

  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  const cardMode = computed(() => (isFullscreen.value ? 'normal' : 'collapse'));

  const baseColumns = computed(() => {
    const columns: InfoColumn[][] = [
      [
        {
          label: t('任务ID'),
          key: 'root_id',
          isCopy: true,
        },
        {
          label: t('任务类型'),
          key: 'ticket_type_display',
        }
      ],
      [
        {
          label: t('开始时间'),
          key: 'created_at',
        },
        {
          label: t('结束时间'),
          key: 'updated_at',
        }
      ],
      [
        {
          label: t('状态'),
          key: '',
          render: () => <DbStatus style="vertical-align: top;" type="linear" theme={getStatusTheme()}>
            <span>{statusText.value || '--'}</span>
          </DbStatus>,
        },
        {
          label: t('耗时'),
          key: '',
          render: () => getCostTimeDisplay(baseInfo.value.cost_time) as string,
        }
      ],
      [
        {
          label: t('执行人'),
          key: 'created_by',
        },
        {
          label: t('关联单据'),
          key: 'uid',
          render: () => (baseInfo.value.uid ? (
            <router-link
              target="_blank"
              to={{
                name: 'bizTicketManage',
                query: {
                  id: baseInfo.value.uid,
                },
              }}>
              {baseInfo.value.uid}
            </router-link>
            ) : '--'),
        }
      ],
    ];

    // 结果文件
    if (showResultFileTypes.includes(baseInfo.value.ticket_type as TicketTypesStrings)
      && baseInfo.value.status === 'FINISHED') {
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

  /**
   * 拓扑全屏切换
   */
  const { isFullscreen, toggle } = useFullscreen(flowTopoRef);

  let expandFailedNodeObjects: TaskflowList = [];
  let expandTodoNodeObjects: TaskflowList = [];
  const expandNodes: string[] = [];
  const showResultFileTypes: TicketTypesStrings[] = [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE];

  watch(() => flowState.details, () => {
    // if (failNodesTreeData.value.length > 0 || todoNodesTreeData.value.length > 0) {
    //   return
    // };
    // failNodesCount.value = 0;

    // if (flowState.details.activities) {
    //   failNodesTreeData.value = flowState.details.flow_info?.status === 'FAILED' ? generateFailNodesTree(flowState.details.activities) : [];

    //   const todoNodeIdList = flowState.details.todos.map(todoItem => todoItem.context.node_id)
    //   todoNodesTreeData.value = todoNodeIdList.length ? generateTodoNodesTree(flowState.details.activities, todoNodeIdList) : [];
    // }

    // 只计算数量，当 待确认节点数 或 失败节点数 变化时，才刷新树结构
    if (flowState.details.activities) {
      let failNodesNum = 0

      const getFailNodesNum = (activities: TaskflowDetails['activities']) => {
        const flowList: TaskflowList = []
        Object.values(activities).forEach(item  => {
          if (item.status === 'FAILED') {
            if (item.pipeline) {
              getFailNodesNum(item.pipeline.activities)
            } else {
              failNodesNum = failNodesNum + 1;
            }
          }
        })
        return flowList;
      }
      getFailNodesNum(flowState.details.activities)

      failNodesCount.value = failNodesNum
    }
  })

  watch(failNodesCount, () => {
    isFindFirstLeafFailNode = false;
    failLeafNodes.value = []
    expandFailedNodeObjects = []
    failNodesTreeData.value = flowState.details.flow_info?.status === 'FAILED' ? generateFailNodesTree(flowState.details.activities) : [];

    setTreeOpen([
      failedTopPreviewNodeTreeRef,
      failedToolPreviewNodeTreeRef
    ])
  })

  watch(todoNodesCount, () => {
    isFindFirstLeafTodoNode = false
    expandTodoNodeObjects = []
    const todoNodeIdList = getTodoNodeIdList(flowState.details)
    todoNodesTreeData.value = todoNodeIdList.length ? generateTodoNodesTree(flowState.details.activities, todoNodeIdList) : [];

    setTreeOpen([
      todoTopPreviewNodeTreeRef,
      todoToolPreviewNodeTreeRef,
    ], false)
  })

  watch(() => baseInfo.value.status, (status) => {
    if (status && flowState.instance === null) {
      setTimeout(() => {
        flowState.instance = new GraphCanvas(`#${flowState.flowSelectorId}`, baseInfo.value);
        flowState.instance
          .on('nodeClick', handleNodeClick)
          .on('nodeMouseEnter', handleNodeMouseEnter)
          .on('nodeMouseLeave', handleNodeMouseLeave);
        retryRenderFailedTips();
      });
    }
  }, {
    immediate: true,
  });

  const getTodoNodeIdList = (details: TaskflowDetails) => {
    const { status } = details.flow_info;
    return (details.todos || []).reduce<string[]>((prevList, todoItem) => {
      if ((status === 'RUNNING' || status === 'FAILED') && todoItem.status === 'TODO') {
        prevList.push(todoItem.context.node_id)
      }
      return prevList
    }, [])
  }

  const generateFailNodesTree = (activities: TaskflowDetails['activities']) => {
    const flowList: TaskflowList = []
    Object.values(activities).forEach(item  => {
      if (item.status === 'FAILED') {
        flowList.push(item);
        if (!isFindFirstLeafFailNode) {
          expandNodes.push(item.id);
          expandFailedNodeObjects.push(item);
        }
        if (item.pipeline) {
          Object.assign(item, {
            failedChildren: generateFailNodesTree(item.pipeline.activities),
          });
        } else {
          isFindFirstLeafFailNode = true;
          // failNodesCount.value = failNodesCount.value + 1;
          failLeafNodes.value.push({ data: _.cloneDeep(item) } as GraphNode)
        }
      }
    })
    return flowList;
  }

  const generateTodoNodesTree = (activities: TaskflowDetails['activities'], nodeList: string[]) => {
    const flowList: TaskflowList = []
    Object.values(activities).forEach((activityItem) => {
      if (activityItem.pipeline) {
        const activityChildren = generateTodoNodesTree(activityItem.pipeline.activities, nodeList)
        Object.assign(activityItem, {
          todoChildren: activityChildren,
        });
        if (activityChildren.length > 0) {
          flowList.push(activityItem)
          if (!isFindFirstLeafTodoNode) {
            isFindFirstLeafTodoNode = true
            expandNodes.push(activityItem.id);
            expandTodoNodeObjects.push(activityItem);
          }
        }
      } else {
        if (nodeList.includes(activityItem.id)) {
          flowList.push(activityItem);
        }
      }
    })
    return flowList;
  }

  const setTreeOpen = (refList: Array<typeof failedTopPreviewNodeTreeRef>, isFailed = true) => {
    refList.forEach((refItem) => {
      if (refItem.value?.isOpen()) {
        handleNodeTreeAfterShow(refItem.value.getTreeRef(), isFailed)
      }
    })
  }

  const handleToolNodeTreeAfterShow = (treeRef: Ref, isFailed = true) => {
    if (isFailed) {
      todoToolPreviewNodeTreeRef.value?.close()
    } else {
      failedToolPreviewNodeTreeRef.value?.close()
    }
    handleNodeTreeAfterShow(treeRef, isFailed)
  }

  const handleNodeTreeAfterShow = (treeRef: Ref, isFailed = true) => {
    setTimeout(() => {
      const expandNodeObjects = isFailed ? expandFailedNodeObjects : expandTodoNodeObjects
      expandNodeObjects.forEach(node => {
        treeRef.value.setOpen(node);
      });

      const leafNode = expandNodeObjects[expandNodeObjects.length - 1];
      treeRef.value.setSelect(leafNode);
    })
  }

  const handleQuickGotoFailNodeLog = (index: number, isNext: boolean) => {
    fetchTaskflowDetails();
    const targetIndex = isNext ? index + 1 : index - 1;
    const targetNode = failLeafNodes.value[targetIndex];
    handleShowLog(targetNode);
  }

  const expandRetractNodes = (node: TaskflowList[number], treeRef: Ref, showLog: boolean) => {
    const children = showLog ? node.failedChildren : node.todoChildren
    // 有子节点则展开
    if (children && children.length > 0) {
      if (!expandNodes.includes(node.id)) {
        expandNodes.push(node.id);
        renderNodes();
      }
    }
    const parentNode = treeRef.value.getParentNode(node)
    if (parentNode) {
      expandRetractNodes(parentNode, treeRef, showLog)
    }
  }

  // 点击父节点展开，点击叶子节点定位
  const handleTreeNodeClick = (node: TaskflowList[number], treeRef: Ref, showLog = true) => {
    // eslint-disable-next-line no-underscore-dangle
    const { scale } = flowState.instance.flowInstance._diagramInstance._canvasTransform;

    expandRetractNodes(node, treeRef, showLog)

    setTimeout(() => {
      const graphNode = flowState.instance.graphData.locations.find((item: GraphNode) => item.data.id === node.id);
      if (showLog) {
        handleShowLog(graphNode);
      }

      const children = showLog ? node.failedChildren : node.todoChildren
      if (!children) {
        const x = ((flowRef.value!.clientWidth / 2) - graphNode.x) * scale;
        const y = ((flowRef.value!.clientHeight / 2) - graphNode.y - 128) * scale;
        flowState.instance?.translate(x, y);
      }
    })
  };

  const getStatusTheme = (isTag = false) => {
    const value = baseInfo.value.status;
    if (isTag && value === 'RUNNING') {
      return 'info'
    };
    const themes = {
      RUNNING: 'loading',
      CREATED: 'default',
      FINISHED: 'success',
    };
    return themes[value as keyof typeof themes] || 'danger' as any;
  };

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
   * 渲染画布节点
   */
  const renderNodes = (updateLogData = false) => {
    const todoNodeIdList = getTodoNodeIdList(flowState.details)
    const { locations, lines } = formatGraphData(flowState.details, expandNodes, todoNodeIdList);
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
   * 渲染失败重试tips
   */
  const retryRenderFailedTips = () => {
    // 渲染失败重试tips
    flowState.instance?.setUpdateCallback(() => {
      if (baseInfo.value.status === 'REVOKED') {
        return;
      }
      setTimeout(() => {
        tippyInstances.value?.forEach?.(t => t.destroy());
        tippyInstances.value = dbTippy(document.querySelectorAll('.operation-icon.db-icon-refresh-2'), {
          content: t('失败重试'),
        });
        skippInstances.value?.forEach?.(t => t.destroy());
        skippInstances.value = dbTippy(document.querySelectorAll('.operation-icon.db-icon-stop'), {
          content: t('跳过'),
        });
        forceFailInstances.value?.forEach?.(t => t.destroy());
        forceFailInstances.value = dbTippy(document.querySelectorAll('.operation-icon.db-icon-qiangzhizhongzhi'), {
          content: t('强制失败'),
        });
        todoInstances.value?.forEach?.(t => t.destroy());
        todoInstances.value = dbTippy(document.querySelectorAll('.operation-icon.db-icon-check'), {
          content: t('确认继续'),
        });
      }, 30);
    });
    // 渲染画布节点
    flowState.instance && renderNodes(true);
  };

  /**
   * 获取任务详情数据
   */
  const fetchTaskflowDetails = (loading = false) => {
    flowState.loading = loading;
    getTaskflowDetails({ rootId: rootId.value }, {
      permission: 'page'
    })
      .then((res) => {
        flowState.details = res;
        retryRenderFailedTips();
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
   * 重试节点
   */
  const handleRefresh = () => {
    retryTaskflowNode({
      root_id: rootId.value,
      node_id: logState.node.id,
    }).then(() => {
      renderNodes();
      fetchTaskflowDetails();
    });
  };

  /**
   * 继续节点
   */
  const handleTodo = (node: GraphNode) => {
    const todoItem = flowState.details.todos!.find(todoItem => todoItem.context.node_id === node.id)
    if (todoItem) {
      ticketBatchProcessTodo({
        action: "APPROVE",
        operations: [
          {
            todo_id: todoItem.id,
            params: {}
          }
        ]})
        .then(() => {
          renderNodes();
          fetchTaskflowDetails();
          messageSuccess(t('继续任务成功'));
        })
    }
  };

  /**
   * 跳过节点
   */
  const handleSkipp = (node: GraphNode) => {
    skipTaskflowNode({
      root_id: rootId.value,
      node_id: node.data.id,
    }).then(() => {
      // eslint-disable-next-line no-param-reassign
      node.data.status = 'SKIPPED';
      renderNodes();
      fetchTaskflowDetails();
    });
  };

  /**
   * 强制失败节点
   */
  const handleForceFail = (node: GraphNode) => {
    forceFailflowNode({
      root_id: rootId.value,
      node_id: node.data.id,
    }).then(() => {
      renderNodes();
      fetchTaskflowDetails();
    });
  };

  const handleTodoAllPipeline = () => {
    ticketBatchProcessTodo({
      action: "APPROVE",
      operations: flowState.details.todos!.map(todoItem => ({
        todo_id: todoItem.id,
        params: {}
      }))
    })
      .then(() => {
        fetchTaskflowDetails();
        messageSuccess(t('继续任务成功'));
      })
  };

  const handleRetryAllPipeline = () => {
    isRetryAllPipeline.value = true;
    batchRetryNodes({
      root_id: rootId.value,
    })
      .then(() => {
        fetchTaskflowDetails();
        messageSuccess(t('失败重试成功'));
      })
      .finally(() => {
        isRetryAllPipeline.value = false;
      });
  };

  const handleRevokePipeline = () => {
    isRevokePipeline.value = true;
    revokePipeline({ rootId: rootId.value })
      .then(() => {
        fetchTaskflowDetails();
        messageSuccess(t('终止任务成功'));
        location.reload();
      })
      .finally(() => {
        isRevokePipeline.value = false;
      });
  };

  const handleShowLog = (node: GraphNode) => {
    logState.isShow = true;
    logState.node = node;
  };

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

      if (eventType === 'force-fail') {
        forceFailState.instance && forceFailState.instance.destroy();
        forceFailState.instance = dbTippy(event.target as HTMLElement, {
          trigger: 'click',
          theme: 'light',
          content: forceFailTipsRef.value,
          arrow: true,
          placement: 'top',
          appendTo: () => document.body,
          interactive: true,
          allowHTML: true,
          hideOnClick: true,
          maxWidth: 400,
          zIndex: 9999,
        });
        forceFailState.instance.show();
        forceFailState.node = node;
        forceFailState.isShow = true;
        return;
      }

      if (eventType === 'todo') {
        todoState.instance && todoState.instance.destroy();
        todoState.instance = dbTippy(event.target as HTMLElement, {
          trigger: 'click',
          theme: 'light',
          content: todoTemplateRef.value,
          arrow: true,
          placement: 'top',
          appendTo: () => document.body,
          interactive: true,
          allowHTML: true,
          hideOnClick: true,
          maxWidth: 400,
          zIndex: 9999,
        });
        todoState.instance.show();
        todoState.node = node;
        todoState.isShow = true;
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
    logState.node = node;
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
    handleRefresh();
    handleRefreshCancel();
  };

  /**
   * 取消继续节点
   */
  const handleTodoCancel = () => {
    if (todoState.instance) {
      todoState.instance.destroy();
    }
    todoState.isShow = false;
  };

  /**
   * 确认继续节点
   */
  const handleTodoClick = () => {
    if (todoState.node) {
      handleTodo(todoState.node);
    }
    handleTodoCancel();
  };

  const handleForceFailClick = () => {
    if (forceFailState.node) {
      handleForceFail(forceFailState.node);
    }
    handleForceFailCancel();
  };

  const handleForceFailCancel = () => {
    forceFailState.instance && forceFailState.instance.destroy();
    forceFailState.isShow = false;
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
      const { x, y } = flowInstance._options.canvasPadding; // eslint-disable-line no-underscore-dangle
      const { scale } = flowInstance._diagramInstance._canvasTransform; // eslint-disable-line no-underscore-dangle
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
    fetchTaskflowDetails(true);

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

  onUnmounted(() => {
    pause();
    flowState.instance?.destroy();
  });

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.push({
          name: 'taskHistoryList',
        });
        return;
      }
      router.push({
        name: route.query.from as string,
      });
    },
  });
</script>

<style lang="less">
  @import '@styles/mixins';

  .mission-detail-page {
    position: relative;
    height: calc(100% - 10px);

    .custom-main-breadcrumbs {
      top: -52px;
    }

    .db-card__content,
    .mission-flows {
      height: 100%;
    }

    .mission-details {
      height: 100%;

      .mission-details-base {
        width: 80%;
        padding-left: 40px;

        .base-info__label {
          min-width: 100px;
          justify-content: flex-end;
        }
      }

      .mission-details-flows {
        height: calc(100% - 150px);
        padding: 14px 0;
        overflow: hidden;
        border-top: 1px solid @border-disable;

        .db-card__header {
          padding: 0 24px;
        }

        .db-card__content {
          padding-top: 14px;
        }
      }

      .flow-tools {
        padding-bottom: 2px;
        .flex-center();

        .flow-tools-icon {
          display: block;
          margin-left: 16px;
          font-size: @font-size-large;
          text-align: center;
          cursor: pointer;
        }

        .flow-tools-icon:hover,
        .flow-tools-icon-active {
          color: @primary-color;
        }
      }
    }

    .hot-key {
      width: 230px;

      .hot-key-title {
        padding-bottom: 8px;
        color: @title-color;
        border-bottom: 1px solid #eaebf0;
      }

      .hot-key-item {
        display: flex;
        padding: 8px 0 6px;
        color: @default-color;
        align-items: center;
      }

      .hot-key-text {
        margin-right: 32px;
      }

      .hot-key-code {
        min-width: 20px;
        padding: 0 6px;
        margin-right: 8px;
        line-height: 18px;
        border: 1px solid #dcdee5;
        border-radius: 2px;
      }
    }
  }

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

  .mission-force-fail-tip {
    width: 280px;
    padding: 12px 0 8px;
    color: @default-color;

    .title {
      font-size: 16px;
      color: #313238;
    }

    .sub-title {
      margin-top: 6px;
      margin-bottom: 16px;
      font-size: 12px;
      color: #63656e;
    }

    .btn {
      width: 100%;
      margin-top: 14px;
      text-align: right;

      .confirm {
        width: 88px;
        color: #fff;
        background: #ea3636;
        border: none;
      }

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
  .box-shadow(@color: rgba(25,25,41,0.1)) {
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

      &[data-evt-type='log'] {
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
          background-image: url('@images/flow-loading.png');
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
          background-color: #000;
          border-radius: 2px;
          opacity: 40%;

          &:hover {
            opacity: 60%;
          }
        }

        [class*='db-icon-'] {
          display: inline-block;
          width: 16px;
          height: 16px;
          font-size: 12px;
          line-height: 16px;
          vertical-align: top;
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

      &--todo {
        .node-ractangle__status {
          background-color: #ff9c01;
        }

        .node-ractangle__text {
          color: #f59500;
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

  .mission-detail-status-box {
    display: flex;
    font-size: 12px;

    .mission-detail-status-info {
      .flex-center();

      margin-right: 24px;
    }

    .mission-detail-status-operate-button {
      padding: 5px 8px;
      border-radius: 50px;

      [class*='db-icon-'] {
        margin-right: 4px;
        font-size: 20px;
      }
    }
  }

  .task-history-fail-num-tip {
    display: inline-block;
    height: 22px;
    padding: 0 8px;
    font-size: 12px;
    line-height: 22px;
    color: #ea3536;
    cursor: pointer;
    background: #fee;
    border-radius: 11px;

    .number-display {
      height: 16px;
      padding: 0 5px;
      margin-left: 5px;
      line-height: 20px;
      color: #fff;
      background: #ea3636;
      border-radius: 8px;
    }
  }
</style>
