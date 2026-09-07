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
    ref="flowCanvasContainerRef"
    class="mission-flows-layout"
    :class="{ 'is-fullscreen': isFullscreen, 'is-minimap-visible': isMinimapVisible }">
    <Tools
      v-model:minimap-visible="isMinimapVisible"
      :is-full-screen="isFullscreen"
      :zoom="canvasZoomValue"
      @reset="handleResetGraph"
      @toggle-full-screen="handleToggleFullScreen"
      @zoom-change="(value) => applyZoom(value)" />
  </div>
  <div style="position: absolute; top: 0; left: 0; display: none">
    <NodeSkip
      ref="skipTemplateRef"
      :data="nodeOperationState.currentNode"
      :root-id="rootId"
      @close="(refresh) => handleCancelOperation('skip', refresh)" />
    <NodeRetry
      ref="retryTemplateRef"
      :data="nodeOperationState.currentNode"
      :root-id="rootId"
      @close="(refresh) => handleCancelOperation('retry', refresh)" />
    <NodeContinue
      ref="continueTemplateRef"
      :data="nodeOperationState.currentNode"
      @close="(refresh) => handleCancelOperation('continue', refresh)" />
    <NodeForceFail
      ref="forceFailTemplateRef"
      :data="nodeOperationState.currentNode"
      :root-id="rootId"
      @close="(refresh) => handleCancelOperation('forceFail', refresh)" />
  </div>
</template>
<script setup lang="tsx">
  import BkAlert from 'bkui-vue/lib/alert';
  import BkForm, { BkFormItem } from 'bkui-vue/lib/form';
  import InfoBox from 'bkui-vue/lib/info-box';
  import BkInput from 'bkui-vue/lib/input';
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { FlowTypes, retryTaskflowNode, skipTaskflowNode } from '@services/source/taskflow';

  import { dbTippy } from '@common/tippy';

  import {
    type FlowModel,
    getNodeDisplayStatus,
    NODE_STATUS_META,
    superUserModeInjectionKey,
  } from '@views/task-history/detail/utils';

  import { messageSuccess } from '@utils';

  import { CanvasEvent, GraphEvent, NodeEvent } from '@antv/g6';
  import { useFullscreen } from '@vueuse/core';

  import NodeContinue from './components/node-operation/Continue.vue';
  import NodeForceFail from './components/node-operation/ForceFail.vue';
  import NodeRetry from './components/node-operation/Retry.vue';
  import NodeSkip from './components/node-operation/Skip.vue';
  import Tools from './components/Tools.vue';
  import { FlowGraph, type Node, ZOOM_MAX, ZOOM_MIN, ZOOM_STEP } from './utils';

  interface Props {
    /** 左侧浮动面板宽度，画布铺满整个容器，定位时要让流程图起点避开被面板遮住的那一段 */
    leftOffset?: number;
    model?: FlowModel;
    rootId?: string;
    searchKey?: string;
  }

  interface Emits {
    (e: 'clickSingleNode', data: Node, isShowAiLog?: boolean): void;
    (e: 'refresh'): void;
    (
      e: 'ready',
      data: {
        nodesCount: number;
      },
    ): void;
  }

  interface Exposes {
    checkContainerInitCanvas: () => void;
    focusNode: (nodeId: string) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    leftOffset: 0,
    model: undefined,
    rootId: '',
    searchKey: '',
  });
  const emits = defineEmits<Emits>();
  const expandedIds = defineModel<string[]>('expandedIds', { required: true });

  // 缩放动画只给工具栏按钮和快捷键用，滚轮要跟手，不能排队等动画
  const ZOOM_ANIMATION = { duration: 500, easing: 'ease' };
  // Firefox 常按「行」上报滚动量，换算成像素后与其它浏览器手感一致
  const WHEEL_LINE_HEIGHT = 16;
  // 滚轮缩放灵敏度：每滚动 1px 对应的缩放百分比。鼠标滚轮一格约 100px，即一格 10%
  const ZOOM_WHEEL_SENSITIVITY = 0.1;

  const { t } = useI18n();

  const isSuperUserMode = inject(superUserModeInjectionKey)!;

  const formRef = ref<InstanceType<typeof BkForm>>();
  const flowCanvasContainerRef = ref<HTMLDivElement>();
  const skipTemplateRef = ref<InstanceType<typeof NodeSkip>>();
  const retryTemplateRef = ref<InstanceType<typeof NodeRetry>>();
  const continueTemplateRef = ref<InstanceType<typeof NodeContinue>>();
  const forceFailTemplateRef = ref<InstanceType<typeof NodeForceFail>>();
  const canvasZoomValue = ref(100);
  const isMinimapVisible = ref(false);

  let flowGraphInstance: FlowGraph | undefined;
  let isPointerInCanvas = false;
  let isReadyEmitted = false;
  // 聚焦要等这一轮的建图 / 重新布局落地，否则节点还没进画布就去取它的位置
  let syncTask: Promise<void> = Promise.resolve();
  let statusTooltip: Instance | null = null;

  const { isFullscreen, toggle } = useFullscreen(flowCanvasContainerRef);

  // 全屏的是画布容器本身，浮动面板不在全屏元素内，这时不用给它让位
  const canvasLeftOffset = computed(() => (isFullscreen.value ? 0 : props.leftOffset));

  const nodeOperationState = reactive({
    currentNode: undefined as Node | undefined,
    instance: null as Instance | null,
    log: {
      isShow: false,
    },
  });

  const formData = reactive({
    remark: '',
  });

  // origin 传视口坐标，只有滚轮缩放需要锚在指针上，按钮与快捷键仍按视口中心缩放
  const applyZoom = (value: number, animate = true, origin?: [number, number]) => {
    const nextZoom = _.clamp(value, ZOOM_MIN, ZOOM_MAX);
    if (nextZoom === canvasZoomValue.value) {
      return;
    }
    canvasZoomValue.value = nextZoom;
    flowGraphInstance?.zoomTo(nextZoom / 100, animate ? ZOOM_ANIMATION : undefined, origin);
  };

  const handleShowTooltip = (e: any) => {
    const { target } = e;
    const status = getNodeDisplayStatus(target.data);
    if (status === 'CREATED') {
      return;
    }

    const { id, style } = target.data;
    let [x, y] = flowGraphInstance!.getElementPosition(id);
    // 右上角状态图标画在卡片右上角，即包围盒的右边缘
    x += style.width / 2;
    y -= 36;
    const [targetX, targetY] = flowGraphInstance!.getClientByCanvas([x, y]);
    statusTooltip?.destroy();
    statusTooltip = dbTippy(document.body, {
      allowHTML: true,
      appendTo: () => flowCanvasContainerRef.value!,
      arrow: true,
      content: NODE_STATUS_META[status].text,
      hideOnClick: true,
      interactive: false,
      maxWidth: 200,
      placement: 'top',
      theme: 'dark',
      trigger: 'manual',
      zIndex: 9999,
    });
    statusTooltip.setProps({
      getReferenceClientRect: () =>
        ({
          bottom: targetY,
          height: 0,
          left: targetX,
          right: targetX,
          top: targetY,
          width: 0,
          x,
          y,
        }) as any,
    });
    statusTooltip.show();
  };

  const handleOperationShowTip = (type: string, e: any) => {
    const contentTemplateMap = {
      continue: continueTemplateRef.value!.getTemplateRef()!,
      forceFail: forceFailTemplateRef.value!.getTemplateRef()!,
      retry: retryTemplateRef.value!.getTemplateRef()!,
      skip: skipTemplateRef.value!.getTemplateRef()!,
    };
    const { target } = e;
    const id = target.data.id;
    let [x, y] = flowGraphInstance!.getElementPosition(id);
    y += 28;
    const { skippable, todoId } = target.data;
    switch (type) {
      case 'continue':
        x -= 68;
        break;
      case 'forceFail':
        if (!todoId) {
          x -= 68;
        } else {
          x += 20;
        }
        break;
      case 'skip':
        x -= 80;
        break;
      case 'retry':
        if (skippable) {
          x -= 16;
        } else {
          x -= 80;
        }
        break;
    }
    const [targetX, targetY] = flowGraphInstance!.getClientByCanvas([x, y]);
    nodeOperationState.instance?.destroy();
    nodeOperationState.instance = dbTippy(document.body, {
      allowHTML: true,
      appendTo: () => flowCanvasContainerRef.value!,
      arrow: true,
      content: contentTemplateMap[type as keyof typeof contentTemplateMap],
      hideOnClick: true,
      interactive: true,
      maxWidth: 400,
      placement: 'top',
      theme: 'light',
      trigger: 'manual',
      zIndex: 9999,
    });
    nodeOperationState.instance.setProps({
      getReferenceClientRect: () =>
        ({
          bottom: targetY,
          height: 0,
          left: targetX,
          right: targetX,
          top: targetY,
          width: 0,
          x,
          y,
        }) as any,
    });
    nodeOperationState.instance.show();
    nodeOperationState.currentNode = target.data;
  };

  const handleCancelOperation = (type: string, refresh: boolean) => {
    if (nodeOperationState.instance) {
      nodeOperationState.instance.destroy();
    }
    if (refresh) {
      emits('refresh');
    }
  };

  const handleForceSkipOrRetry = (
    type: 'forceSkip' | 'forceRetry',
    params: {
      id: string;
      name: string;
    },
  ) => {
    const typeInfo = {
      forceRetry: {
        api: retryTaskflowNode,
        confirmText: t('确认强制重试'),
        subtitle: t('强制重试将重新执行当前失败节点，执行成功后继续执行后续节点'),
        title: t('确认强制重试该节点？'),
      },
      forceSkip: {
        api: skipTaskflowNode,
        confirmText: t('确认强制跳过'),
        subtitle: t('强制跳过将忽略当前节点的失败状态，直接执行后续节点。当前节点将标记为 失败手动跳过'),
        title: t('确认强制跳过该节点？'),
      },
    };

    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      confirmText: typeInfo[type].confirmText,
      content: () => (
        <>
          <BkAlert
            theme='warning'
            title={t('此操作将绕过系统预设的流程控制，请确认已知晓风险')}
          />
          <div class='mission-flows-retry-and-skip-info mt-12'>
            <div class='name-box'>
              <span class='name-label'>{t('节点名称')}：</span>
              <span>{params.name}</span>
            </div>
            <div>{typeInfo[type].subtitle}</div>
          </div>
          <BkForm
            ref={formRef}
            class='mt-20'
            form-type='vertical'
            model={formData}>
            <BkFormItem
              label={t('操作原因')}
              property='remark'
              required>
              <BkInput
                v-model={formData.remark}
                class='mt-6'
                placeholder={t('请输入操作原因')}
                type='textarea'
              />
            </BkFormItem>
          </BkForm>
        </>
      ),
      infoType: 'warning',
      onConfirm: async function () {
        await formRef.value!.validate();
        // 必须 await，请求失败时抛出让 InfoBox 保持打开
        await typeInfo[type].api({
          is_force: true,
          node_id: params.id,
          remark: formData.remark,
          root_id: props.rootId,
        });
        Object.assign(formData, { remark: '' });
        messageSuccess(t('操作成功'));
        emits('refresh');
      },
      theme: 'danger',
      title: typeInfo[type].title,
    });
  };

  const toggleExpand = (id: string) => {
    expandedIds.value = expandedIds.value.includes(id)
      ? expandedIds.value.filter((item) => item !== id)
      : [...expandedIds.value, id];
  };

  /**
   * 定位到节点并高亮。
   * 调用方可能刚改了展开状态，先让 watch 把这一轮布局排上队，再等它落地，
   * 否则会在节点还没进画布时去取它的位置
   */
  const focusNode = async (nodeId: string) => {
    await nextTick();
    await syncTask;
    const graph = flowGraphInstance;
    if (!graph || !graph.getNodeData().some((item) => item.id === nodeId)) {
      return;
    }
    graph.moveNodeIntoView(nodeId, canvasLeftOffset.value);
    graph.updateFocusNode(nodeId);
    graph.updateCanvasState();
  };

  const bindGraphEvents = () => {
    const graph = flowGraphInstance!;

    graph.on(NodeEvent.CLICK, (e: any) => {
      const { originalTarget, target } = e;
      // 所有画布的点击事件都在这里统一处理，提升性能
      const { className } = originalTarget;
      const { id, name } = target.data;
      const params = {
        id,
        name,
      };

      if (className.startsWith('manualConfirm')) {
        // 确认继续
        handleOperationShowTip('continue', e);
        return;
      }
      if (className.startsWith('forceFail')) {
        // 强制失败
        handleOperationShowTip('forceFail', e);
        return;
      }
      if (className.startsWith('skip')) {
        // 跳过
        handleOperationShowTip('skip', e);
        return;
      }
      if (className.startsWith('forceSkip')) {
        // 强制跳过
        handleForceSkipOrRetry('forceSkip', params);
        return;
      }
      if (className.startsWith('retry')) {
        // 失败重试
        if (isSuperUserMode.value) {
          handleForceSkipOrRetry('forceRetry', params);
        } else {
          handleOperationShowTip('retry', e);
        }
        return;
      }
      if (className.startsWith('forceRetry')) {
        // 强制失败重试
        handleForceSkipOrRetry('forceRetry', params);
        return;
      }
      if (className.startsWith('aiLogAnalysis')) {
        // 日志解析
        emits('clickSingleNode', target.data, true);
        return;
      }
      if (target.data.type === FlowTypes.ServiceActivity) {
        emits('clickSingleNode', target.data);
      }
      if (target.data.type === FlowTypes.SubProcess) {
        toggleExpand(target.data.id);
      }

      focusNode(target.data.id);
    });

    graph.on(NodeEvent.POINTER_ENTER, (e: any) => {
      if (e.originalTarget.className === 'rightTopBackground') {
        handleShowTooltip(e);
      }
    });

    graph.on(NodeEvent.POINTER_LEAVE, () => {
      statusTooltip?.destroy();
      statusTooltip = null;
    });

    graph.on(CanvasEvent.CLICK, () => {
      nodeOperationState.log.isShow = false;
    });

    // 只监听 AFTER_RENDER：展开折叠会增删节点，聚焦节点可能被重建，这里补一次聚焦态。
    // 不能挂到 AFTER_DRAW 上——hover 走的 setElementState 也会触发 draw，
    // 而 setElementState 是全量替换状态，会把刚加上的 hover 态又抹掉
    graph.on(GraphEvent.AFTER_RENDER, () => {
      if (graph.focusNodeId) {
        graph.updateFocusNode(graph.focusNodeId, true);
      }
      // 拓扑在运行期是固定的，节点总数只用于外层决定轮询频率，报一次就够
      if (!isReadyEmitted && props.model) {
        isReadyEmitted = true;
        emits('ready', {
          nodesCount: props.model.nodeMap.size,
        });
      }
    });
  };

  const handleWheel = (e: WheelEvent) => {
    const scale = e.deltaMode === 1 ? WHEEL_LINE_HEIGHT : 1;
    if (e.ctrlKey) {
      e.preventDefault();
      // 缩放量与滚动量成正比，但仍以 ZOOM_STEP 为最小单位取整：
      // 滚得少至少走一步，滚得多一次走多步，触控板与鼠标滚轮的手感才能拉平
      const direction = e.deltaY < 0 ? 1 : -1;
      const step = Math.max(ZOOM_STEP, Math.round(Math.abs(e.deltaY) * scale * ZOOM_WHEEL_SENSITIVITY));
      applyZoom(
        canvasZoomValue.value + direction * step,
        false,
        flowGraphInstance?.getViewportByClient([e.clientX, e.clientY]),
      );
      return;
    }
    // 两个方向一起给，触控板的斜向滚动才不会被掰成正交方向；滚动向下时画布内容要往上走
    flowGraphInstance?.translateBy([-e.deltaX * scale, -e.deltaY * scale]);
  };

  const handleKeydown = (e: KeyboardEvent) => {
    // 容器不可聚焦，键盘事件只能挂在 window 上，用指针位置界定这几个快捷键的作用范围
    if (!e.ctrlKey || !isPointerInCanvas) {
      return;
    }
    if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      applyZoom(canvasZoomValue.value + ZOOM_STEP);
      return;
    }
    if (e.key === '-') {
      e.preventDefault();
      applyZoom(canvasZoomValue.value - ZOOM_STEP);
      return;
    }
    if (e.key === '0') {
      e.preventDefault();
      handleResetGraph();
    }
  };

  const handlePointerEnter = () => {
    isPointerInCanvas = true;
  };

  const handlePointerLeave = () => {
    isPointerInCanvas = false;
  };

  const syncGraph = (relayout: boolean) => {
    if (!props.model || !flowCanvasContainerRef.value) {
      return syncTask;
    }

    const input = {
      expandedIds: expandedIds.value,
      isSuperUserMode: isSuperUserMode.value,
      model: props.model,
      searchKey: props.searchKey,
    };

    const runSync = async () => {
      if (flowGraphInstance) {
        await flowGraphInstance.applyInput(input, relayout);
        return;
      }
      flowGraphInstance = new FlowGraph(flowCanvasContainerRef.value!);
      await flowGraphInstance.initGraph(input);
      // 事件只能绑一次，而且要赶在首次绘制之前绑好，AFTER_RENDER 才收得到
      bindGraphEvents();
      await flowGraphInstance.render();
    };

    // 串起来排队执行：建图、重新布局、轮询刷新可能同时在途，并发落地会互相覆盖。
    // 任一环出错都不能让队列停在 rejected 状态，否则后续刷新全部失效，所以这里收口
    syncTask = syncTask.then(runSync).catch((error) => {
      console.error('flow canvas render failed:', error);
    });

    return syncTask;
  };

  watch([() => props.model, () => props.searchKey], () => {
    syncGraph(false);
  });

  watch(expandedIds, () => {
    syncGraph(true);
  });

  watch(isSuperUserMode, async () => {
    await syncGraph(false);
    // 顶部的专家模式提示条会占掉一段高度，容器跟着变矮或变高，画布尺寸必须同步，
    // 否则视口仍按旧高度算，节点会偏、底边会被裁掉
    await nextTick();
    const graph = flowGraphInstance;
    if (!graph) {
      return;
    }
    const [, previousHeight] = graph.getSize();
    graph.resize();
    const [, nextHeight] = graph.getSize();
    // 画布高度变化后视口中心跟着挪了这段差值的一半，补回去才不会看着像整体跳了一下
    graph.translateBy([0, (nextHeight - previousHeight) / 2]);
  });

  const handleToggleFullScreen = () => {
    toggle();
  };

  // 全屏切换后容器尺寸才变，布局坐标与容器大小无关，同步画布尺寸即可，不必重建
  watch(isFullscreen, async () => {
    await nextTick();
    flowGraphInstance?.resize();
  });

  // 窗口尺寸变化只需同步画布尺寸，不必重建整张图；resize 事件触发很密集，这里防抖
  const handleWindowResize = _.debounce(() => {
    flowGraphInstance?.resize();
  }, 200);

  const handleResetGraph = () => {
    applyZoom(100);
    // 有聚焦节点优先定位到聚焦节点
    if (flowGraphInstance?.focusNodeId) {
      flowGraphInstance.focusElement(flowGraphInstance.focusNodeId, canvasLeftOffset.value);
      return;
    }

    flowGraphInstance?.translateTo([canvasLeftOffset.value, 100]);
  };

  const checkContainerCanvas = async () => {
    // 建图是异步的，页签切过来时这一轮可能还没落地。画布的视口要等首次渲染才建起来，
    // 在那之前定位会抛错，位置丢掉后内容就贴在画布原点上
    await syncTask;
    if (!flowGraphInstance || !flowCanvasContainerRef.value) {
      return;
    }
    const { width } = flowCanvasContainerRef.value.getBoundingClientRect();
    const [canvasWidth] = flowGraphInstance.getSize();
    // 容器比画布宽说明建图时所在的 Tab 还没显示出来，同步一下画布尺寸即可
    if (width > canvasWidth) {
      flowGraphInstance.resize();
    }
    flowGraphInstance.translateTo([canvasLeftOffset.value, 100]);
  };

  onMounted(() => {
    const container = flowCanvasContainerRef.value!;
    // 强制 passive:false，Ctrl + 滚轮要拦掉浏览器自身的缩放
    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('pointerenter', handlePointerEnter);
    container.addEventListener('pointerleave', handlePointerLeave);
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('resize', handleWindowResize);
    syncGraph(false);
  });

  onBeforeUnmount(() => {
    const container = flowCanvasContainerRef.value;
    container?.removeEventListener('wheel', handleWheel);
    container?.removeEventListener('pointerenter', handlePointerEnter);
    container?.removeEventListener('pointerleave', handlePointerLeave);
    window.removeEventListener('keydown', handleKeydown);
    window.removeEventListener('resize', handleWindowResize);
    handleWindowResize.cancel();
    statusTooltip?.destroy();
    nodeOperationState.instance?.destroy();
    flowGraphInstance?.destroy();
  });

  defineExpose<Exposes>({
    checkContainerInitCanvas: () => {
      checkContainerCanvas();
    },
    focusNode,
  });
</script>
<style lang="less">
  .mission-flows-layout {
    position: relative;
    width: 100%;
    height: 100%;
    background-color: #f5f7fa;

    &.is-fullscreen {
      width: 100% !important;
      height: 100vh !important;
    }

    // 缩略图由 G6 的 minimap 插件挂到容器里，显隐交给容器上的类名控制，
    // 不去查它的 DOM：插件会在重新建图时把这个节点整个换掉
    .g6-minimap {
      top: 56px !important;
      right: 16px !important;
      left: auto !important;
      display: none !important;
      border: none !important;
      border-radius: 4px;
      box-shadow: 0 1px 6px 0 #0000001f;
    }

    &.is-minimap-visible .g6-minimap {
      display: block !important;
    }
  }

  .mission-flows-retry-and-skip-info {
    padding: 12px 16px;
    line-height: 22px;
    color: #4d4f56;
    text-align: left;
    background: #f5f6fa;
    border-radius: 2px;

    .name-box {
      .name-label {
        color: #979ba5;
      }
    }
  }
</style>
