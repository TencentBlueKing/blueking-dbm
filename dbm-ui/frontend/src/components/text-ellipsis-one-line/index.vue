<template>
  <div
    ref="mainRef"
    class="text-ellipsis-one-line-box">
    <BkButton
      v-bk-tooltips="{
        content: text,
        disabled: !isOverflow
      }"
      class="text-main"
      :style="[{'flex': isOverflow ? 1 : 'none'}, textStyle]"
      text
      theme="primary"
      @click="handleClickText">
      <div
        ref="rowRef"
        class="text">
        {{ text }}
      </div>
    </BkButton>
    <slot />
  </div>
</template>
<script setup lang="ts">
  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    text?: string,
    textStyle?: Record<string, string>
  }

  interface Emits {
    (e: 'click'): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    text: '',
    textStyle: undefined,
  });

  const emits = defineEmits<Emits>();

  function checkOveflow() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      // eslint-disable-next-line max-len
      isOverflow.value = rowRef.value.scrollWidth > rowRef.value.clientWidth || mainRef.value.scrollWidth > mainRef.value.clientWidth;
    });
  }

  const mainRef = ref();
  const rowRef = ref();
  const isOverflow = ref(true);

  let timer = 0;

  watch(() => props.text, () => {
    checkOveflow();
  }, {
    immediate: true,
  });


  useResizeObserver(mainRef, checkOveflow);

  const handleClickText = () => {
    emits('click');
  };
</script>
<style lang="less">
.text-ellipsis-one-line-box {
  display: flex;
  width: 100%;
  align-items: center;

  .text-main {
    margin-right: 4px;
    overflow: hidden;
    // flex: 1;

    .bk-button-text {
      display: inline-block;
      width: 100%;
      overflow: hidden;

      .text {
        width: 100%;
        height: 18px;
        overflow: hidden;
        line-height: 18px;
        text-align: left;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}
</style>
