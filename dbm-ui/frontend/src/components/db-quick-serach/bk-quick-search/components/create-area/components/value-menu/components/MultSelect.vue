<template>
  <div
    ref="root"
    class="bk-quick-search-type-mult-select"
    :style="{ width: contentMinWidth > 0 ? `${contentMinWidth + 12}px` : '' }">
    <div ref="layout">
      <div
        v-for="(valueItem, index) in renderList"
        :key="valueItem.value"
        class="value-item"
        :class="{ active: activeIndex === index }"
        @click="handleChange(valueItem)">
        <Checkbox
          :checked="Boolean(checkedMap[valueItem.value])"
          style="pointer-events: none" />
        {{ valueItem.label }}
      </div>
    </div>
    <div
      v-if="keyword && renderList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ keyword }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { Checkbox } from 'tdesign-vue-next';
  import { computed, onMounted, ref, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@/components/db-quick-serach/bk-quick-search/hooks/useMenuKeyboard';

  interface Props {
    keyword: string;
    list: {
      label: string;
      value: string | number;
    }[];
  }

  interface IResult {
    label: string;
    value: string | number;
  }

  type Emits = (e: 'change', value: IResult[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IResult[]>({
    default: () => [],
  });

  const rootRef = useTemplateRef('root');
  const layoutRef = useTemplateRef('layout');
  const localValue = ref<Props['list']>([]);
  const contentMinWidth = ref(0);

  const checkedMap = computed(() =>
    localValue.value.reduce(
      (result, item) =>
        Object.assign(result, {
          [item.value]: true,
        }),
      {} as Record<string, boolean>,
    ),
  );

  const renderList = computed(() => {
    const keyword = `${props.keyword || ''}`.trim().toLowerCase();
    if (!keyword) {
      return props.list;
    }

    return _.filter(props.list, (item) => item.label.toLowerCase().includes(keyword));
  });

  let isInnerSelfChange = false;
  watch(
    modelValue,
    () => {
      if (isInnerSelfChange) {
        isInnerSelfChange = false;
        return;
      }

      localValue.value = [...modelValue.value];
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.list,
    () => {
      nextTick(() => {
        contentMinWidth.value = Math.max(layoutRef.value!.getBoundingClientRect().width, contentMinWidth.value);
      });
    },
  );

  const handleChange = (data: IResult) => {
    if (checkedMap.value[data.value]) {
      localValue.value = _.filter(localValue.value, (item) => item.value !== data.value);
    } else {
      localValue.value = [...localValue.value, data];
    }

    isInnerSelfChange = true;
    emits('change', [...localValue.value]);
  };

  const { activeIndex } = useMenuKeyboard(renderList, rootRef, (value) => {
    handleChange(value);
  });

  onMounted(() => {
    contentMinWidth.value = layoutRef.value!.getBoundingClientRect().width;
  });
</script>
<style lang="less">
  .bk-quick-search-type-mult-select {
    padding: 8px 0;
  }
</style>
