<template>
  <div
    ref="menuRef"
    class="bk-quick-search-type-mult-select">
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
  import { computed, ref, toRef } from 'vue';

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

  const localList = toRef(props, 'list');

  const menuRef = ref();
  const localValue = ref<Props['list']>([]);

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
      return localList.value;
    }

    return _.filter(localList.value, (item) => item.label.toLowerCase().includes(keyword));
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

  const handleChange = (data: IResult) => {
    if (checkedMap.value[data.value]) {
      localValue.value = _.filter(localValue.value, (item) => item.value !== data.value);
    } else {
      localValue.value = [...localValue.value, data];
    }

    isInnerSelfChange = true;
    emits('change', [...localValue.value]);
  };

  const { activeIndex } = useMenuKeyboard(renderList, menuRef, (value) => {
    handleChange(value);
  });
</script>
<style lang="less">
  .bk-quick-search-type-mult-select {
    padding: 8px 0;
  }
</style>
