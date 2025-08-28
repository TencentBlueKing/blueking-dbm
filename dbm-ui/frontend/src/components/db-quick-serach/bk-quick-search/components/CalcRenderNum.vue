<template>
  <div
    ref="root"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 0; visibility: hidden">
    <div style="display: flex">
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
  const tagRefs = ref<InstanceType<typeof ValueTag>[]>();

  const renderValuText = (value: IValue) => {
    const tagConfig = _.find(props.data, (item) => item.id === value.id) as Props['data'][number];
    return getValuesText(value.values, tagConfig);
  };

  const calcTagSize = _.throttle(
    () => {
      if (!currentInstance?.proxy?.$el) {
        return;
      }
      const valueTagElList = (
        Array.from(currentInstance?.proxy?.$el.parentNode.querySelectorAll('[role="search-value"]')) as HTMLDivElement[]
      ).slice(0, modelValue.value);

      if (props.fouced) {
        valueTagElList.forEach((elItem) => {
          const textEl = elItem.querySelector('.bk-quick-search-value-tag-text') as HTMLDivElement;
          if (textEl) {
            textEl.style.maxWidth = 'unset';
          }
        });
        return;
      }
      const { width: maxWidth } = rootRef.value!.getBoundingClientRect();

      const spaceWidth = props.valueList.length > modelValue.value ? 180 : 150;

      const tagMaxWidth = (maxWidth - spaceWidth) / valueTagElList.length;

      const longTagList: HTMLDivElement[] = [];
      const smallTagList: HTMLDivElement[] = [];
      let smallWidthOffset = 0;
      valueTagElList.forEach((elItem) => {
        const tagRenderWidth = elItem.getBoundingClientRect().width;
        if (tagRenderWidth > tagMaxWidth) {
          longTagList.push(elItem);
        } else {
          smallTagList.push(elItem);
          smallWidthOffset += tagMaxWidth - tagRenderWidth;
        }
      });

      const longWidthOffset = Math.max(smallWidthOffset / longTagList.length - longTagList.length * 8, 0);

      longTagList.forEach((elItem) => {
        const textEl = elItem.querySelector('.bk-quick-search-value-tag-text') as HTMLDivElement;
        if (!textEl) {
          return;
        }

        const labelWidth = elItem.querySelector('.bk-quick-search-value-tag-label')!.getBoundingClientRect().width;

        textEl.style.maxWidth = `${longWidthOffset + tagMaxWidth - labelWidth}px`;
      });
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
      nextTick(() => {
        if (!rootRef.value || !tagRefs.value) {
          return;
        }

        const { width: maxWidth } = rootRef.value!.getBoundingClientRect();
        let calcCount = 0;
        let renderTagTotalWidth = 0;

        tagRefs.value!.forEach((tag) => {
          renderTagTotalWidth += tag.$el.getBoundingClientRect().width;
          if (renderTagTotalWidth >= maxWidth - calcCount * 4 - 20) {
            return;
          }
          calcCount += 1;
        });

        if (props.valueList.length >= 3) {
          modelValue.value = Math.max(calcCount, 3);
        } else {
          modelValue.value = props.valueList.length;
        }

        if (!props.fouced) {
          nextTick(() => {
            calcTagSize();
          });
        }
      });
    },
    {
      immediate: true,
    },
  );

  watch(() => props.fouced, calcTagSize, {
    immediate: true,
  });
</script>
