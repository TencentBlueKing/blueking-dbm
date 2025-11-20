<template>
  <div
    ref="root"
    data-role="calc-render-num"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 0; visibility: hidden">
    <div
      v-if="isShow"
      style="display: flex">
      <ValueTag
        v-for="valueItem in valueList"
        :key="valueItem.id"
        ref="tagRefs"
        style="flex: 0 0 auto">
        {{ valueItem.name }}
        <template #value>
          {{ renderValuText(valueItem) }}
        </template>
      </ValueTag>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { getCurrentInstance, nextTick, ref, useTemplateRef, watch } from 'vue';

  import type { IValue, Props as ContextProps } from '../Index.vue';
  import { getValuesText } from '../utils';

  import ValueTag from './ValueTag.vue';

  interface Props {
    data: ContextProps['data'];
    fouced: boolean;
    valueList: IValue[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>({
    default: 0,
    required: true,
  });

  const currentInstance = getCurrentInstance();

  const rootRef = useTemplateRef('root');
  const isShow = ref(false);
  const tagRefs = ref<InstanceType<typeof ValueTag>[]>();

  const renderValuText = (value: IValue) => {
    const tagConfig = _.find(props.data, (item) => item.id === value.id) as Props['data'][number];
    return getValuesText(value.values, tagConfig);
  };

  const calcTagSize = _.throttle(
    () => {
      if (!currentInstance?.proxy?.$el || !rootRef.value) {
        isShow.value = false;
        return;
      }
      const renderValueTagElList = (
        Array.from(currentInstance?.proxy?.$el.parentNode.querySelectorAll('[role="search-value"]')) as HTMLDivElement[]
      ).slice(0, modelValue.value);
      if (renderValueTagElList.length < 1) {
        return;
      }

      if (props.fouced) {
        renderValueTagElList.forEach((elItem) => {
          const textEl = elItem.querySelector('.bk-quick-search-value-tag-text') as HTMLDivElement;
          if (textEl) {
            textEl.style.maxWidth = 'unset';
          }
        });
        isShow.value = false;
        return;
      }
      const { width: maxWidth } = rootRef.value.getBoundingClientRect();

      const spaceWidth =
        props.valueList.length > modelValue.value
          ? Math.max(modelValue.value * 35 + 80, 130)
          : Math.max(modelValue.value * 35 + 50, 100);

      const tagMaxWidth = (maxWidth - spaceWidth) / renderValueTagElList.length;

      const longTagList: HTMLDivElement[] = [];
      const smallTagList: HTMLDivElement[] = [];
      let smallWidthOffset = 0;
      renderValueTagElList.forEach((elItem) => {
        const tagRenderWidth = elItem.getBoundingClientRect().width;
        if (tagRenderWidth > tagMaxWidth) {
          longTagList.push(elItem);
        } else {
          smallTagList.push(elItem);
          smallWidthOffset += tagMaxWidth - tagRenderWidth;
        }
      });

      const longWidthOffset = Math.max(smallWidthOffset / (longTagList.length || 1) - longTagList.length * 8, 0);

      longTagList.forEach((elItem) => {
        const textEl = elItem.querySelector('.bk-quick-search-value-tag-text') as HTMLDivElement;
        if (!textEl) {
          return;
        }

        const labelWidth = elItem.querySelector('.bk-quick-search-value-tag-label')!.getBoundingClientRect().width;

        textEl.style.maxWidth = `${Math.max(longWidthOffset + tagMaxWidth - labelWidth, 24)}px`;
      });
      isShow.value = false;
    },
    60,
    {
      leading: false,
      trailing: true,
    },
  );

  watch(
    () => props.valueList,
    () => {
      isShow.value = true;
      nextTick(() => {
        if (!rootRef.value || !tagRefs.value) {
          return;
        }

        setTimeout(() => {
          const { width: maxWidth } = rootRef.value!.getBoundingClientRect();
          let calcRealNeedRenderTagCount = 0;
          let renderTagTotalWidth = 0;

          // 计算 tag 的宽度总和是否超出容器宽度
          for (const tagInst of tagRefs.value!) {
            renderTagTotalWidth += tagInst.$el.getBoundingClientRect().width;
            if (renderTagTotalWidth >= maxWidth - calcRealNeedRenderTagCount * 4 - 20) {
              break;
            }
            calcRealNeedRenderTagCount += 1;
          }

          if (calcRealNeedRenderTagCount === props.valueList.length) {
            modelValue.value = props.valueList.length;
            return;
          }

          // 根据最大宽度响应式 tag 渲染策略
          if (maxWidth < 180) {
            // 折叠所有 tag
            modelValue.value = 0;
          } else if (maxWidth < 280) {
            // 最大渲染一个 tag
            const maxCount = 1;
            const hasEnoughTags = props.valueList.length >= maxCount;
            const minRenderCount = hasEnoughTags ? maxCount : props.valueList.length;
            modelValue.value = Math.max(calcRealNeedRenderTagCount, minRenderCount);
          } else if (maxWidth < 400) {
            // 最大渲染 2 个 tag
            const maxCount = 2;
            const hasEnoughTags = props.valueList.length >= maxCount;
            const minRenderCount = hasEnoughTags ? maxCount : props.valueList.length;
            modelValue.value = Math.max(calcRealNeedRenderTagCount, minRenderCount);
          } else {
            // 最大渲染 3 个 tag
            const maxCount = 3;
            const hasEnoughTags = props.valueList.length >= maxCount;
            const minRenderCount = hasEnoughTags ? maxCount : props.valueList.length;
            modelValue.value = Math.max(calcRealNeedRenderTagCount, minRenderCount);
          }

          if (!props.fouced) {
            nextTick(() => {
              calcTagSize();
            });
          }
        });
      });
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.fouced,
    () => {
      isShow.value = true;
      calcTagSize();
    },
    {
      immediate: true,
    },
  );
</script>
