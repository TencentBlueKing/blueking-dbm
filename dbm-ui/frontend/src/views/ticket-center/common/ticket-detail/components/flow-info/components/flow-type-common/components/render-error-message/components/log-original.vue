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
    <div
      ref="logContent"
      v-bk-loading="{ loading: isLoadingLogContent }"
      class="log-content">
      <h1
        v-if="activeNode"
        class="log-node-title">
        {{ activeNode.node_name }}
      </h1>
      <div
        ref="logScroller"
        class="log-scroller"
        @scroll.passive="handleScroll">
        <div
          v-if="isPrependLoading"
          class="prepend-loading">
          {{ t('日志加载中...') }}
        </div>
        <div
          v-bk-xss-html="renderLogContent"
          style="word-break: break-all; white-space: pre-wrap" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import Dayjs from 'dayjs';
  import { useRequest } from 'vue-request';

  import FlowMode from '@services/model/ticket/flow';
  import { getNodeLog, getSpecificNodes } from '@services/source/taskflow';

  import { t } from '@locales/index';

  type NodeLogItem = ServiceReturnType<typeof getNodeLog>['results'][number];

  interface Props {
    data: FlowMode<unknown, any>;
  }
  type Emits = (e: 'elementHeightChange', height: number) => void;
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const rootRef = useTemplateRef<HTMLDivElement>('root');
  const logContentRef = useTemplateRef<HTMLDivElement>('logContent');
  const logScrollerRef = useTemplateRef<HTMLDivElement>('logScroller');
  const activeNode = ref<{
    node_id: string;
    node_name: string;
    version_id: string;
  }>();

  // 日志行高估算值（12px 字号 + 行距），用于换算首屏 1.5 视口的分片条数
  const LOG_LINE_HEIGHT = 20;
  const MIN_LOG_PAGE_SIZE = 30;

  // 已加载的日志（旧 → 新），首片为尾部最新的分片，向上滚动时向前拼接更早内容
  const logList = ref<NodeLogItem[]>([]);
  const isLoadingLogContent = ref(false);
  const isPrependLoading = ref(false);
  // 上一片返回的游标与是否还有更早内容
  let prevSearchAfter: (number | string)[] = [];
  let hasMorePrev = false;
  let logToken = 0;
  // 首片使用的初始 limit，后续每一片请求都原样带上
  let firstPageSize = 0;

  const renderLogContent = computed(() => {
    if (props.data.err_msg) {
      return props.data.err_msg;
    }
    return logList.value
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

  watch(renderLogContent, () => {
    nextTick(() => {
      emits('elementHeightChange', rootRef.value?.getBoundingClientRect().height || 0);
    });
  });

  /**
   * 首屏分片条数取 1.5 倍可视高度（按行高估算）
   */
  const getFirstPageSize = () => {
    const height = logContentRef.value?.getBoundingClientRect().height || 0;
    return Math.max(Math.ceil((height * 1.5) / LOG_LINE_HEIGHT), MIN_LOG_PAGE_SIZE);
  };

  const scrollToBottom = () => {
    nextTick(() => {
      if (logScrollerRef.value) {
        logScrollerRef.value.scrollTop = logScrollerRef.value.scrollHeight;
      }
    });
  };

  const handleClick = (node: { node_id: string; node_name: string; version_id: string }) => {
    activeNode.value = node;
    const token = (logToken += 1);
    logList.value = [];
    prevSearchAfter = [];
    hasMorePrev = false;
    isLoadingLogContent.value = true;

    const limit = getFirstPageSize();
    firstPageSize = limit;

    getNodeLog({
      limit,
      node_id: node.node_id,
      root_id: props.data.flow_obj_id,
      version_id: node.version_id,
    })
      .then((page) => {
        if (token !== logToken) {
          return;
        }
        prevSearchAfter = page.search_after;
        hasMorePrev = page.has_data === true;
        logList.value = page.results;
        // 首屏为日志尾部，定位到最下方
        scrollToBottom();
      })
      .finally(() => {
        if (token === logToken) {
          isLoadingLogContent.value = false;
        }
      });
  };

  /**
   * 向上加载更早内容：滚动到顶且还有上一片时触发
   * DOM 前插后按新增高度补偿 scrollTop，保持视口不跳
   */
  const fetchPrevChunk = async () => {
    if (!hasMorePrev || isPrependLoading.value || isLoadingLogContent.value || !activeNode.value) {
      return;
    }
    const token = logToken;
    isPrependLoading.value = true;
    try {
      const page = await getNodeLog({
        limit: firstPageSize,
        node_id: activeNode.value.node_id,
        root_id: props.data.flow_obj_id,
        search_after: prevSearchAfter,
        version_id: activeNode.value.version_id,
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

      const scroller = logScrollerRef.value;
      const prevHeight = scroller?.scrollHeight ?? 0;
      logList.value = [...chunk, ...logList.value];
      nextTick(() => {
        if (scroller) {
          scroller.scrollTop += scroller.scrollHeight - prevHeight;
        }
      });
    } finally {
      isPrependLoading.value = false;
    }
  };

  const handleScroll = () => {
    if (logScrollerRef.value?.scrollTop === 0) {
      fetchPrevChunk();
    }
  };
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

    .log-content {
      display: flex;
      max-height: inherit;
      min-height: 48px;
      padding-left: 16px;
      overflow: hidden;
      flex: 1;
      flex-direction: column;

      /* 节点名固定在滚动区外，不随内容滚动 */
      .log-node-title {
        height: 20px;
        margin: 0 0 8px;
        overflow: hidden;
        font-size: 12px;
        font-weight: bold;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .log-scroller {
        min-height: 0;
        overflow-y: auto;
        flex: 1;

        /* 与 ScrollFaker 的浅色滚动条规格一致：6px，hover 加宽到 14px */
        &::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }

        &::-webkit-scrollbar-thumb {
          background-color: rgb(151 155 165 / 80%);
          border-radius: 3px;
        }

        &::-webkit-scrollbar-track {
          background: transparent;
        }

        &:hover {
          &::-webkit-scrollbar {
            width: 14px;
          }

          &::-webkit-scrollbar-thumb {
            border-radius: 7px;
          }
        }
      }

      .prepend-loading {
        display: flex;
        height: 24px;
        justify-content: center;
        align-items: center;
        font-size: 12px;
        color: #979ba5;
      }
    }
  }
</style>
