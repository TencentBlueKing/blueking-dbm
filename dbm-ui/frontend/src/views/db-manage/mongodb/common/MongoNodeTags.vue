<template>
  <BkTag
    v-if="data.instance_role"
    class="ml-4"
    size="small">
    {{ data.instance_role }}
  </BkTag>
  <BkTag
    v-if="displayState"
    class="ml-4"
    size="small">
    {{ displayState }}
  </BkTag>
  <BkTag
    v-if="showSegRange && data.seg_range"
    class="ml-4"
    size="small">
    {{ data.seg_range }}
  </BkTag>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import type { ClusterListNode } from '@services/types';

  /** 常见从节点/未初始化状态刷屏，隐藏；PRIMARY 等其它状态仍展示 */
  const HIDDEN_MONGO_STATES = new Set(['NOT_INITIALIZED', 'SECONDARY']);

  interface Props {
    data: Pick<ClusterListNode, 'instance_role' | 'mongodb_state' | 'seg_range'>;
    /** ShardSvr 列表可展示分片名；拓扑表用分组标题，传 false */
    showSegRange?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    showSegRange: false,
  });

  const displayState = computed(() => {
    const state = props.data.mongodb_state;
    if (!state || HIDDEN_MONGO_STATES.has(state)) {
      return '';
    }
    return state;
  });
</script>
