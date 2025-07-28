<template>
  <div>
    <div
      ref="rootRef"
      class="render-entries"
      :style="`width: ${width}px`">
      <div
        v-for="(item, index) in data.slice(0, overflowMaxCount)"
        :key="item"
        class="render-entries-item">
        <div class="render-entries-row">
          <div ref="itemRef">{{ item }}</div>
          <slot
            :data="item"
            :index="index"
            name="append" />
        </div>
      </div>
      <div
        v-if="data.length > overflowMaxCount"
        class="icon-box">
        <DbIcon type="more" />
      </div>
    </div>
    <div style="display: none">
      <div ref="popRef">
        <div
          v-for="item in data"
          :key="item">
          <span>{{ item }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { onBeforeUnmount, onMounted, ref } from 'vue';

  interface Props {
    data: string[];
  }

  const props = defineProps<Props>();

  const rootRef = ref();
  const popRef = ref();
  const itemRef = ref();
  const width = ref(0);
  let tippyIns: Instance | undefined;
  const overflowMaxCount = 10;

  onMounted(() => {
    if (itemRef.value) {
      const widths = (itemRef.value || []).map((item) => item.clientWidth);
      width.value = Math.max(...widths);
    }
    if (props.data.length > overflowMaxCount) {
      tippyIns = tippy(rootRef.value as SingleTarget, {
        appendTo: () => document.body,
        arrow: true,
        content: popRef.value,
        hideOnClick: true,
        interactive: true,
        maxWidth: 'none',
        offset: [0, 0],
        placement: 'top',
        trigger: 'mouseenter',
        zIndex: 999999,
      });
    }
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>

<style lang="less" scoped>
  .render-entries {
    padding: 8px 0;

    .render-entries-item {
      line-height: 22px;

      .render-entries-row {
        display: flex;
        align-items: center;
      }
    }

    .icon-box {
      display: inline-block;
      transform: rotate(90deg);
    }
  }
</style>
