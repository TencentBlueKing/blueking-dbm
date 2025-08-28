<template>
  <div
    ref="root"
    class="bk-quick-search-type-mult-select"
    :style="{ width: contentMinWidth > 0 ? `${contentMinWidth + 12}px` : '' }">
    <div class="bk-quick-search-type-menu-filter-box">
      <Input
        v-model="serachKey"
        borderless
        clearable
        placeholder="请输入关键字">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <div
      ref="layout"
      class="bk-quick-search-value-wrapper">
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
      v-if="serachKey && renderList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ serachKey }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Checkbox, Input } from 'tdesign-vue-next';
  import { computed, onMounted, ref, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@/components/db-quick-serach/bk-quick-search/hooks/useMenuKeyboard';

  interface Props {
    list: {
      label: string;
      value: string | number;
    }[];
    remoteSearch: boolean;
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
  const serachKey = ref('');

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
    const keyword = `${serachKey.value || ''}`.trim().toLowerCase();
    if (!keyword || props.remoteSearch) {
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
    padding: 8px 12px;
  }
</style>
