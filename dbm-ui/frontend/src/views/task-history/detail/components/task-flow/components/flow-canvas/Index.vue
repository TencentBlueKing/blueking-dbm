<template>
  <div
    id="flowCanvasContainer"
    ref="flowCanvasContainerRef"
    class="mission-flows-layout"
    :class="{ 'is-fullscreen': isFullscreen }">
    <Tools
      ref="toolsRef"
      v-model:zoom="canvasZoomValue"
      @reset="handleResetGraph"
      @toggle-full-screen="handleToggleFullScreen"
      @zoom-change="handleZoomChange" />
  </div>
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
</template>
<script setup lang="tsx">
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { FlowTypes } from '@services/source/taskflow';

  import { dbTippy } from '@common/tippy';

  import { CanvasEvent, GraphEvent, NodeEvent } from '@antv/g6';
  import { useFullscreen } from '@vueuse/core';

  import NodeContinue from './components/node-operation/Continue.vue';
  import NodeForceFail from './components/node-operation/ForceFail.vue';
  import NodeRetry from './components/node-operation/Retry.vue';
  import NodeSkip from './components/node-operation/Skip.vue';
  import Tools from './components/Tools.vue';
  import { type Edge, type FlowDetail, FlowGraph, type Node } from './utils';

  interface Props {
    data?: FlowDetail;
    rootId?: string;
  }

  interface Emits {
    (e: 'clickSingleNode', data: any): void;
    (e: 'refresh'): void;
  }

  interface Exposes {
    checkContainerInitCanvas: () => void;
    getGraph: () => FlowGraph | null;
    getShareData: () => {
      edgesMap: Record<string, Set<string>>;
      nodesMap: Record<string, Node>;
      totalEdges: Edge[];
    };
    initGraph: () => void;
    updateCanvasState: () => void;
  }

  type TooltipKey = keyof typeof tooltipState;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    rootId: '',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let flowGraphInstance: FlowGraph;

  const toolsRef = ref<InstanceType<typeof Tools>>();
  const flowCanvasContainerRef = ref<HTMLDivElement | null>(null);
  const skipTemplateRef = ref<InstanceType<typeof NodeSkip>>();
  const retryTemplateRef = ref<InstanceType<typeof NodeRetry>>();
  const continueTemplateRef = ref<InstanceType<typeof NodeContinue>>();
  const forceFailTemplateRef = ref<InstanceType<typeof NodeForceFail>>();
  const canvasZoomValue = ref(100);

  const tooltipState = reactive({
    failed: {
      instance: null as Instance | null,
      isShow: false,
      text: t('执行失败'),
    },
    finished: {
      instance: null as Instance | null,
      isShow: false,
      text: t('执行成功'),
    },
    running: {
      instance: null as Instance | null,
      isShow: false,
      text: t('执行中'),
    },
    skip: {
      instance: null as Instance | null,
      isShow: false,
      text: t('已跳过'),
    },
    todo: {
      instance: null as Instance | null,
      isShow: false,
      text: t('待继续'),
    },
  });

  const { isFullscreen, toggle } = useFullscreen(flowCanvasContainerRef);

  const nodeOperationState = reactive({
    currentNode: undefined as Node | undefined,
    instance: null as Instance | null,
    log: {
      isShow: false,
    },
  });

  const initEvent = () => {
    const container = document.getElementById('flowCanvasContainer')!;
    container.addEventListener(
      'wheel',
      (e: any) => {
        if (e.ctrlKey) {
          e.preventDefault();
          if (e.deltaY < 0) {
            if (flowGraphInstance.viewZoom < 1.5) {
              flowGraphInstance.viewZoom += 0.25;
            }
          } else {
            if (flowGraphInstance.viewZoom > 0.25) {
              flowGraphInstance.viewZoom -= 0.25;
            }
          }

          flowGraphInstance.zoomTo(flowGraphInstance.viewZoom);
          canvasZoomValue.value = flowGraphInstance.viewZoom * 100;
        } else {
          if (Math.abs(e.wheelDeltaX) > Math.abs(e.wheelDeltaY)) {
            const horizontalDistance = e.wheelDeltaX > 0 ? 25 : -25; // 向右滚向右，向左滚向左
            flowGraphInstance.translateBy([horizontalDistance, 0]);
          } else {
            const verticalDistance = e.wheelDeltaY > 0 ? 25 : -25; // 向下滚向下，向上滚向上
            flowGraphInstance.translateBy([0, verticalDistance]);
          }
        }
      },
      { passive: false },
    ); // 强制设置 passive:false

    container.addEventListener(
      'keydown',
      (e: any) => {
        e.preventDefault();
        if (e.ctrlKey && (e.key === '+' || e.key === '=')) {
          toolsRef.value!.zoomIn();
        }
        if (e.ctrlKey && e.key === '-') {
          toolsRef.value!.zoomOut();
        }
        if (e.ctrlKey && e.key === '0') {
          toolsRef.value!.zoomReset();
        }
      },
      { passive: false },
    );
  };

  const initGraph = async (data = props.data) => {
    if (!data) {
      return;
    }

    if (!flowGraphInstance) {
      flowGraphInstance = new FlowGraph('flowCanvasContainer');
      initEvent();
    }
    await flowGraphInstance.initGraph(data);
    flowGraphInstance.on(NodeEvent.CLICK, async (e: any) => {
      const { originalTarget, target } = e;
      // 所有画布的点击事件都在这里统一处理，提升性能
      const { className } = originalTarget;
      if (className.startsWith('manualConfirm')) {
        // 跳过
        handleOperationShowTip('continue', e);
        return;
      }
      if (className.startsWith('forceFail')) {
        // 跳过
        handleOperationShowTip('forceFail', e);
        return;
      }
      if (className.startsWith('skip')) {
        // 跳过
        handleOperationShowTip('skip', e);
        return;
      }
      if (className.startsWith('retry')) {
        // 失败重试
        handleOperationShowTip('retry', e);
        return;
      }
      if (target.data.type === FlowTypes.ServiceActivity) {
        emits('clickSingleNode', target);
      }
      if (target.data.type === FlowTypes.SubProcess) {
        await flowGraphInstance.collapseNode(target.data.id, !target.data.isExpand);
      }

      setTimeout(() => {
        flowGraphInstance.updateFocusNode(target.data.id);
        flowGraphInstance.updateCanvasState();
      });
    });

    flowGraphInstance.on(NodeEvent.POINTER_ENTER, (e: any) => {
      const { originalTarget, target } = e;
      const targetName = originalTarget.className;
      if (targetName === 'rightTopBackground') {
        const status = target.data.status;
        switch (status) {
          case 'RUNNING':
            if (target.data.todoId) {
              handleShowTooltip('todo', e);
            } else {
              handleShowTooltip('running', e);
            }
            break;
          case 'FAILED':
            handleShowTooltip('failed', e);
            break;
          case 'FINISHED':
            if (target.data.skip) {
              handleShowTooltip('skip', e);
            } else {
              handleShowTooltip('finished', e);
            }
            break;
          default:
            break;
        }
      }
    });

    flowGraphInstance.on(NodeEvent.POINTER_LEAVE, () => {
      Object.keys(tooltipState).forEach((key) => {
        const type = key as TooltipKey;
        tooltipState[type].isShow = false;
        tooltipState[type].instance?.destroy();
      });
    });

    flowGraphInstance.on(CanvasEvent.CLICK, () => {
      nodeOperationState.log.isShow = false;
    });

    flowGraphInstance.on(GraphEvent.AFTER_RENDER, () => {
      if (flowGraphInstance.focusNodeId) {
        flowGraphInstance.updateFocusNode(flowGraphInstance.focusNodeId, true);
      }
      setTimeout(() => {
        toolsRef.value!.showMiniMap();
      }, 500);
    });

    await flowGraphInstance.render();
  };

  watch(
    () => props.data,
    () => {
      if (props.data) {
        initGraph();
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowTooltip = (type: TooltipKey, e: any) => {
    const { target } = e;
    const { id, isSubProcess } = target.data;
    let [x, y] = flowGraphInstance.getElementPosition(id);
    x += isSubProcess ? 127 : 120;
    y -= 36;
    const [targetX, targetY] = flowGraphInstance.getClientByCanvas([x, y]);
    tooltipState[type].instance?.destroy();
    tooltipState[type].instance = dbTippy(document.body, {
      allowHTML: true,
      appendTo: () => flowCanvasContainerRef.value!,
      arrow: true,
      content: tooltipState[type].text,
      hideOnClick: true,
      interactive: false,
      maxWidth: 200,
      placement: 'top',
      theme: 'dark',
      trigger: 'manual',
      zIndex: 9999,
    });
    tooltipState[type].instance.setProps({
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
    tooltipState[type].instance.show();
    tooltipState[type].isShow = true;
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
    let [x, y] = flowGraphInstance.getElementPosition(id);
    y += 32;
    const { skippable, todoId } = target.data;
    switch (type) {
      case 'continue':
        x -= 76;
        break;
      case 'forceFail':
        if (!todoId) {
          x -= 76;
        } else {
          x += 12;
        }
        break;
      case 'skip':
        x -= 88;
        break;
      case 'retry':
        if (skippable) {
          x -= 24;
        } else {
          x -= 88;
        }
        break;
    }
    const [targetX, targetY] = flowGraphInstance.getClientByCanvas([x, y]);
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

  const handleZoomChange = (zoom: number) => {
    flowGraphInstance.zoomTo(zoom / 100, {
      duration: 500,
      easing: 'ease',
    });
  };

  const handleToggleFullScreen = () => {
    toggle();
    setTimeout(() => {
      initGraph();
    }, 100);
  };

  const handleInitGraph = () => {
    initGraph();
  };

  const handleResetGraph = () => {
    // 有聚焦节点优先定位到聚焦节点
    if (flowGraphInstance.focusNodeId) {
      flowGraphInstance.focusElement(flowGraphInstance.focusNodeId);
      return;
    }

    flowGraphInstance.translateTo([0, 100]);
  };

  onMounted(() => {
    window.addEventListener('resize', handleInitGraph);
  });

  onUnmounted(() => {
    flowGraphInstance?.destroy();
    window.removeEventListener('resize', handleInitGraph);
  });

  defineExpose<Exposes>({
    checkContainerInitCanvas: async () => {
      const { width } = flowCanvasContainerRef.value!.getBoundingClientRect();
      const [canvasWidth] = flowGraphInstance.getSize();
      if (width > canvasWidth) {
        await initGraph();
        // flowGraphInstance.isInit = true;
      }
      flowGraphInstance.graph?.translateTo([0, 100]);
    },
    getGraph: () => flowGraphInstance,
    getShareData: () => ({
      edgesMap: flowGraphInstance.edgesMap,
      nodesMap: flowGraphInstance.nodesMap,
      totalEdges: flowGraphInstance.totalEdges,
    }),
    initGraph: () => initGraph(props.data),
    updateCanvasState: () => flowGraphInstance.updateCanvasState,
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
  }
</style>
