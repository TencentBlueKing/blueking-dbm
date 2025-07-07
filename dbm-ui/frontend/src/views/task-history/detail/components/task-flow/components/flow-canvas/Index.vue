<template>
  <div
    id="flowCanvasContainer"
    ref="flowCanvasContainerRef"
    class="mission-flows-layout"
    :class="{ 'is-fullscreen': isFullscreen }">
    <Tools
      ref="toolsRef"
      v-model:zoom="canvasZoomValue"
      @toggle-full-screen="handleToggleFullScreen"
      @zoom-change="handleZoomChange" />
  </div>
  <NodeSkip
    ref="skipTemplateRef"
    :data="nodeOperationState.currentNode"
    :is-show="nodeOperationState.operate.skip.isShow"
    :root-id="rootId"
    @close="(refresh) => handleCancelOperation('skip', refresh)" />
  <NodeRetry
    ref="retryTemplateRef"
    :data="nodeOperationState.currentNode"
    :is-show="nodeOperationState.operate.retry.isShow"
    :root-id="rootId"
    @close="(refresh) => handleCancelOperation('retry', refresh)" />
  <NodeContinue
    ref="continueTemplateRef"
    :data="nodeOperationState.currentNode"
    :is-show="nodeOperationState.operate.continue.isShow"
    @close="(refresh) => handleCancelOperation('continue', refresh)" />
  <NodeForceFail
    ref="forceFailTemplateRef"
    :data="nodeOperationState.currentNode"
    :is-show="nodeOperationState.operate.forceFail.isShow"
    :root-id="rootId"
    @close="(refresh) => handleCancelOperation('forceFail', refresh)" />
</template>
<script setup lang="tsx">
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { FlowTypes } from '@services/source/taskflow';

  import { dbTippy } from '@common/tippy';

  import { CanvasEvent, ContainerEvent, GraphEvent, NodeEvent } from '@antv/g6';
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
      collapsedMap: Record<string, { edges: Edge[]; nodes: Node[] }>;
      edgesMap: Record<string, Set<string>>;
      graphData: {
        edges: Edge[];
        nodes: Node[];
      };
      nodesMap: Record<string, Node>;
      totalEdges: Edge[];
    };
    initGraph: () => void;
    updateCanvasState: () => void;
  }

  type OperationKey = keyof (typeof nodeOperationState)['operate'];
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

  const nodeOperationState = reactive({
    currentNode: undefined as Node | undefined,
    log: {
      isShow: false,
    },
    operate: {
      continue: {
        instance: null as Instance | null,
        isShow: false,
      },
      forceFail: {
        instance: null as Instance | null,
        isShow: false,
      },

      retry: {
        instance: null as Instance | null,
        isShow: false,
      },
      skip: {
        instance: null as Instance | null,
        isShow: false,
      },
    },
  });

  const tooltipState = reactive({
    running: {
      instance: null as Instance | null,
      isShow: false,
      text: t('执行中'),
    },
    todo: {
      instance: null as Instance | null,
      isShow: false,
      text: t('待继续'),
    },
  });

  const { isFullscreen, toggle } = useFullscreen(flowCanvasContainerRef);

  const initGraph = async (data = props.data) => {
    if (!data) {
      return;
    }
    if (!flowGraphInstance) {
      flowGraphInstance = new FlowGraph('flowCanvasContainer');
    }
    await flowGraphInstance.initGraph(data);
    flowGraphInstance.on(NodeEvent.CLICK, (e: any) => {
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
        // 展开节点
        // 设置collapsed到内部属性
        target.data.collapsed = !target.data.collapsed;
        // 同步collapsed到全局node
        const currentNode = flowGraphInstance.graphData.nodes.find((item) => item.id === target.data.id);
        if (currentNode) {
          currentNode.collapsed = target.data.collapsed;
        }
        flowGraphInstance.collapseNode(target.data, target.data.collapsed);
        flowGraphInstance.render();
        if (flowGraphInstance.searchObj.key) {
          setTimeout(() => {
            flowGraphInstance.focusElement(target.data.id);
          });
        }
      }
    });

    flowGraphInstance.on(NodeEvent.POINTER_ENTER, (e: any) => {
      if (e.originalTarget.className === 'todoBackground') {
        handleShowTooltip('todo', e);
        return;
      }
      if (e.originalTarget.className === 'loadingBackground') {
        handleShowTooltip('running', e);
        return;
      }
    });

    flowGraphInstance.on(NodeEvent.POINTER_LEAVE, () => {
      Object.keys(tooltipState).forEach((key) => {
        const type = key as TooltipKey;
        tooltipState[type].isShow = false;
        tooltipState[type].instance?.destroy();
      });
    });

    flowGraphInstance.on(CanvasEvent.WHEEL, () => {
      const zoom = Math.floor(flowGraphInstance.viewZoom * 100);
      canvasZoomValue.value = zoom;
    });

    flowGraphInstance.on(CanvasEvent.CLICK, () => {
      nodeOperationState.log.isShow = false;
    });

    flowGraphInstance.on(GraphEvent.AFTER_RENDER, () => {
      setTimeout(() => {
        toolsRef.value!.showMiniMap();
      }, 500);
    });

    flowGraphInstance.on(ContainerEvent.KEY_DOWN, (e: KeyboardEvent) => {
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
    y -= 42;
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

  const handleOperationShowTip = (type: OperationKey, e: any) => {
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
    nodeOperationState.operate[type].instance?.destroy();
    nodeOperationState.operate[type].instance = dbTippy(document.body, {
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
    nodeOperationState.operate[type].instance.setProps({
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
    nodeOperationState.operate[type].instance.show();
    nodeOperationState.currentNode = target.data;
    nodeOperationState.operate[type].isShow = true;
  };

  const handleCancelOperation = (type: OperationKey, refresh: boolean) => {
    if (nodeOperationState.operate[type].instance) {
      nodeOperationState.operate[type].instance.destroy();
    }
    nodeOperationState.operate[type].isShow = false;
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

  onUnmounted(() => {
    flowGraphInstance.destroy();
  });

  defineExpose<Exposes>({
    checkContainerInitCanvas: async () => {
      const { width } = flowCanvasContainerRef.value!.getBoundingClientRect();
      const [canvasWidth] = flowGraphInstance.getSize();
      if (width > canvasWidth) {
        await initGraph();
        flowGraphInstance.isInit = true;
        flowGraphInstance.fitView();
      }
    },
    getGraph: () => flowGraphInstance,
    getShareData: () => ({
      collapsedMap: flowGraphInstance.collapsedMap,
      edgesMap: flowGraphInstance.edgesMap,
      graphData: flowGraphInstance.graphData,
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
