<template>
  <div
    ref="root"
    v-bk-loading="{ loading: isLoading, opacity: 0.1 }"
    class="ticket-detail-flow-info-render-error-message-log-original">
    <div
      v-if="specificNodeList && specificNodeList.length > 1 && !data.err_msg"
      class="log-node-list">
      <ScrollFaker>
        <div
          v-for="item in specificNodeList"
          :key="item.node_id"
          class="log-node-item"
          :class="{
            'is-active': activeNode?.node_id === item.node_id,
          }"
          @click="handleClick(item)">
          {{ item.node_name }}
        </div>
      </ScrollFaker>
    </div>
    <div class="log-main">
      <div
        v-bk-loading="{ loading: isLoadingLogContent }"
        class="log-content">
        <ScrollFaker
          :key="activeNode?.node_id"
          ref="scrollFakerRef">
          <h1 style="font-size: 12px; font-weight: bold">{{ activeNode?.node_name }}</h1>
          <div
            ref="logDetailRef"
            v-bk-xss-html="renderLogContent"
            style="word-break: break-all; white-space: pre-wrap" />
        </ScrollFaker>
      </div>
      <div
        v-if="isTooLarge"
        class="log-export-tip mt-4">
        {{ t('日志过大，页面仅展示部分内容，更多内容请下载') }}
        <a
          :download="`${activeNode?.node_id}.log`"
          :href="exportLogUrl">
          {{ t('完整日志') }}
        </a>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import Dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import FlowMode from '@services/model/ticket/flow';
  import { getNodeLogV2, getSpecificNodes } from '@services/source/taskflow';

  interface Props {
    data: FlowMode<unknown, any>;
  }
  type Emits = (e: 'elementHeightChange', height: number) => void;
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const { t } = useI18n();
  const rootRef = useTemplateRef<HTMLDivElement>('root');
  const scrollFakerRef = useTemplateRef<{ scrollTo: (scrollLeft: number, scrollTop: number) => void }>(
    'scrollFakerRef',
  );
  const activeNode = ref<{
    node_id: string;
    node_name: string;
    version_id: string;
  }>();

  // 后端标记日志过大（页面仅展示部分），底部展示导出入口
  const isTooLarge = ref(false);

  const renderLogContent = computed(() => {
    if (props.data.err_msg) {
      return props.data.err_msg;
    }
    if (props.data.err_msg || !logContent.value) {
      return '';
    }
    return logContent.value.result
      .map(
        (item) =>
          `<span style="font-weight: 500">[${Dayjs(Number(item.timestamp)).format('YYYY-MM-DD HH:mm:ss')} ${item.levelname}]</span> ${item.message}`,
      )
      .join('\n');
  });

  const { data: specificNodeList, loading: isLoading } = useRequest(getSpecificNodes, {
    defaultParams: [
      {
        root_id: props.data.flow_obj_id,
        status: FlowMode.STATUS_FAILED,
      },
    ],
    manual: Boolean(props.data.err_msg),
    onSuccess: (data) => {
      if (data.length > 0) {
        handleClick(data[0]);
      }
    },
  });

  const {
    data: logContent,
    loading: isLoadingLogContent,
    run: runGetNodeLog,
  } = useRequest(getNodeLogV2, {
    manual: true,
    onSuccess: (data) => {
      isTooLarge.value = data.too_large;
    },
  });

  // 日志内容渲染完成后通过 ScrollFaker 的 scrollTo 滚到底部
  // 传极大值由浏览器钳制到可滚动范围，无需知道 scrollHeight；逐帧校准覆盖 xss 渲染的时序差异
  const scrollLogToBottom = () => {
    let frameCount = 0;
    const scrollFrame = () => {
      scrollFakerRef.value?.scrollTo(0, Number.MAX_SAFE_INTEGER);
      if (frameCount < 5) {
        frameCount += 1;
        requestAnimationFrame(scrollFrame);
      }
    };
    nextTick(() => {
      requestAnimationFrame(scrollFrame);
    });
  };

  watch(renderLogContent, () => {
    nextTick(() => {
      scrollLogToBottom();
      emits('elementHeightChange', rootRef.value?.getBoundingClientRect().height || 0);
    });
  });

  const handleClick = (node: { node_id: string; node_name: string; version_id: string }) => {
    activeNode.value = node;
    runGetNodeLog({
      node_id: node.node_id,
      root_id: props.data.flow_obj_id,
      version_id: node.version_id,
    });
  };

  // node_log_v2 接口带 download=true，返回完整日志附件，浏览器直接保存
  const exportLogUrl = computed(() => {
    if (!activeNode.value) {
      return 'javascript:';
    }
    const params = new URLSearchParams({
      node_id: activeNode.value.node_id,
      version_id: activeNode.value.version_id,
    });
    return `/apis/taskflow/${props.data.flow_obj_id}/node_log_v2/?${params.toString()}&download=true`;
  });
</script>
<style lang="postcss">
  .ticket-detail-flow-info-render-error-message-log-original {
    position: relative;
    display: flex;
    height: 100%;
    max-height: inherit;
    overflow: hidden;

    .log-node-list {
      max-width: 200px;
      max-height: inherit;
      padding-right: 16px;
      border-right: 1px solid #fdd;
      gap: 12px;
      flex: 1 1 auto;

      .log-node-item {
        display: flex;
        height: 28px;
        max-width: inherit;
        padding: 12px;
        overflow: hidden;
        font-size: 12px;
        color: #4d4f56;
        text-overflow: ellipsis;
        white-space: nowrap;
        cursor: pointer;
        background: #fff;
        border-radius: 2px;
        align-items: center;

        &:hover {
          background: #cddffe;
        }

        &.is-active {
          color: #fff;
          background: #3a84ff;
        }

        & ~ .log-node-item {
          margin-top: 8px;
        }
      }
    }

    .log-main {
      display: flex;
      max-height: inherit;
      min-width: 0;
      padding-left: 16px;
      flex-direction: column;
      flex: 1;

      .log-content {
        max-height: inherit;
        min-height: 48px;
        flex: 1;
      }
    }

    .log-export-tip {
      display: flex;
      height: 28px;
      padding: 0 16px 0 0;
      font-size: 12px;
      color: #ff9c01;
      background: #fff4e2;
      align-items: center;

      a {
        margin-left: 4px;
        color: #3a84ff;
        cursor: pointer;
      }
    }
  }
</style>
