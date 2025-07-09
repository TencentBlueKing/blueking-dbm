<template>
  <div>
    <div
      v-if="flodTagCount > 0"
      ref="popHandler"
      class="bk-quick-search-tag-flod"
      @mouseenter="handleMouseenter">
      +{{ flodTagCount }}
    </div>
    <div ref="popContent">
      <ValueTag
        v-for="(tagValue, index) in renderList"
        :key="index"
        :removeable="false">
        {{ tagValue.name }}
        <template #value>
          {{ renderValuText(tagValue) }}
        </template>
      </ValueTag>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, nextTick, onBeforeUnmount, useTemplateRef, watch } from 'vue';

  import type { IValue, Props as ContextProps } from '../Index.vue';
  import { getValuesText } from '../utils';

  import ValueTag from './ValueTag.vue';

  interface Props {
    data: ContextProps['data'];
    renderTagCount: number;
    valueList: IValue[];
  }

  const props = defineProps<Props>();
  const popHandlerRef = useTemplateRef('popHandler');
  const popContentRef = useTemplateRef('popContent');
  const flodTagCount = computed(() => props.valueList.length - props.renderTagCount);
  const renderList = computed(() => props.valueList.slice(props.renderTagCount));

  const renderValuText = (value: IValue) => {
    const tagConfig = _.find(props.data, (item) => item.id === value.id) as Props['data'][number];
    return getValuesText(value.values, tagConfig);
  };

  let popInstance: Instance | undefined;

  watch(
    flodTagCount,
    () => {
      nextTick(() => {
        if (!popHandlerRef.value || !popContentRef.value) {
          return;
        }
        if (flodTagCount.value < 1 && popInstance) {
          popInstance.hide();
          popInstance.destroy();
          popInstance = undefined;
          return;
        }

        popInstance = tippy(popHandlerRef.value as SingleTarget, {
          appendTo: () => document.body,
          arrow: true,
          content: popContentRef.value as HTMLElement,
          hideOnClick: false,
          interactive: false,
          offset: [0, 8],
          placement: 'top',
          theme: 'light',
          trigger: 'mouseenter',
          zIndex: 9999,
        });
      });
    },
    {
      immediate: true,
    },
  );

  const handleMouseenter = () => {
    // if (popInstance) {
    //   popInstance.show();
    // }
  };

  onBeforeUnmount(() => {
    if (popInstance) {
      popInstance.destroy();
      popInstance = undefined;
    }
  });
</script>
<style lang="less">
  .bk-quick-search-tag-flod {
    display: inline-flex;
    height: 22px;
    align-items: center;
    padding: 0 8px;
    margin-top: 4px;
    margin-right: 4px;
    overflow: hidden;
    line-height: 22px;
    color: #63656e;
    cursor: pointer;
    background: #f0f1f5;
    border-radius: 2px;
    flex: 0 0 auto;
  }
</style>
