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
      v-bk-loading="{ loading: isLoadingLogContent }"
      class="log-content">
      <ScrollFaker :key="activeNode?.node_id">
        <h1 style="font-size: 12px; font-weight: bold">{{ activeNode?.node_name }}</h1>
        <div
          v-bk-xss-html="renderLogContent"
          style="word-break: break-all; white-space: pre-wrap" />
      </ScrollFaker>
    </div>
  </div>
</template>
<script setup lang="ts">
  import Dayjs from 'dayjs';
  import { useRequest } from 'vue-request';

  import FlowMode from '@services/model/ticket/flow';
  import { getNodeLog, getSpecificNodes } from '@services/source/taskflow';

  interface Props {
    data: FlowMode<unknown, any>;
  }
  type Emits = (e: 'elementHeightChange', height: number) => void;
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const rootRef = useTemplateRef<HTMLDivElement>('root');
  const activeNode = ref<{
    node_id: string;
    node_name: string;
  }>();

  const renderLogContent = computed(() => {
    if (props.data.err_msg) {
      return props.data.err_msg;
    }
    if (props.data.err_msg || !logContent.value) {
      return '';
    }
    return logContent.value
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
        status: props.data.status,
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
  } = useRequest(getNodeLog, {
    manual: true,
  });

  watch(renderLogContent, () => {
    nextTick(() => {
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
      max-height: inherit;
      min-height: 48px;
      padding-left: 16px;
      flex: 1;
    }
  }
</style>
