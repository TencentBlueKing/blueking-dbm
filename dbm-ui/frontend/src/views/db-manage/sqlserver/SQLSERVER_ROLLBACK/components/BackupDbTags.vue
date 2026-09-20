<template>
  <span v-if="!list?.length">--</span>
  <div
    v-else
    class="backup-db-tags">
    <DbTag
      v-for="name in visibleList"
      :key="name"
      :theme="theme">
      {{ name }}
    </DbTag>
    <DbTag
      v-if="overflowCount > 0"
      key="more"
      ref="moreRef"
      :theme="theme">
      +{{ overflowCount }}
    </DbTag>
    <div style="display: none">
      <div
        ref="tippyPanelRef"
        class="backup-db-tippy-panel">
        <DbTag
          v-for="name in overflowList"
          :key="name"
          :theme="theme">
          {{ name }}
        </DbTag>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { type Instance, type SingleTarget } from 'tippy.js';

  import { dbTippy } from '@common/tippy';

  import DbTag from '@components/bkui-vue/tag/Index.vue';

  const props = defineProps<{
    list: string[];
    theme?: '' | 'danger' | 'success' | 'warning' | 'info' | undefined;
  }>();

  const MAX_VISIBLE = 2;

  const overflowCount = computed(() => Math.max(0, props.list.length - MAX_VISIBLE));
  const visibleList = computed(() => props.list.slice(0, MAX_VISIBLE));
  const overflowList = computed(() => props.list.slice(MAX_VISIBLE));

  const moreRef = ref<InstanceType<typeof DbTag>>();
  const tippyPanelRef = ref<HTMLElement>();

  let tippyInst: Instance | undefined;

  const initTippy = () => {
    if (!overflowCount.value || !moreRef.value?.$el || !tippyPanelRef.value) return;

    tippyInst = dbTippy(moreRef.value.$el as SingleTarget, {
      allowHTML: true,
      appendTo: () => document.body,
      arrow: true,
      content: tippyPanelRef.value,
      hideOnClick: true,
      interactive: true,
      maxWidth: 400,
      offset: [0, 8],
      placement: 'top',
      theme: 'light',
      trigger: 'mouseenter',
      zIndex: 999999,
    });
  };

  onMounted(() => {
    nextTick(() => {
      initTippy();
    });
  });

  onBeforeUnmount(() => {
    if (tippyInst) {
      tippyInst.hide();
      tippyInst.unmount();
      tippyInst.destroy();
    }
  });
</script>
<style lang="less" scoped>
  .backup-db-tags {
    display: inline-flex;
    flex-wrap: nowrap;
    gap: 4px;
  }

  .backup-db-tippy-panel {
    margin-top: -8px;

    .dbm-tag {
      margin-top: 8px;
    }
  }
</style>
