<template>
  <div
    ref="root"
    class="bk-quick-search-type-mult-select"
    :style="{ width: contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
    <div class="bk-quick-search-value-panel-filter-box">
      <Input
        v-model="filterKey"
        autofocus
        borderless
        clearable
        placeholder="请输入关键字">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <BkLoading :loading="isRemoteListLoading">
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
        v-if="filterKey && renderList.length < 1 && !isRemoteListLoading"
        class="bk-quick-search-value-panel-filter-empty">
        <BkException
          description="搜索为空"
          scene="part"
          type="search-empty" />
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Checkbox, Input } from 'tdesign-vue-next';
  import { computed, onMounted, ref, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@components/db-quick-search/bk-quick-search/hooks/useMenuKeyboard';
  import type { Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { makeMap } from '@components/db-quick-search/bk-quick-search/utils';

  import useMenuList from '../hooks/useMenuList';

  interface Props {
    config: ContextProps['data'][number];
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

  const defaultModelValue = [...modelValue.value];

  const { filterKey, list, loading: isRemoteListLoading } = useMenuList<IResult>(props.config);

  const layoutRef = useTemplateRef('layout');
  const localValue = ref<IResult[]>([]);
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
    if (props.config.remoteSearch) {
      return list.value;
    }
    const keyword = `${filterKey.value || ''}`.trim().toLowerCase();
    if (!keyword) {
      const modelValueMap = makeMap(defaultModelValue.map((item) => item.value));
      return [...defaultModelValue, ..._.filter(list.value, (item) => !modelValueMap[item.value])];
    }
    return _.filter(list.value, (item) => item.label.toLowerCase().includes(keyword));
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
    list,
    () => {
      if (list.value.length < 1) {
        return;
      }
      nextTick(() => {
        contentMinWidth.value = Math.max(layoutRef.value!.getBoundingClientRect().width, contentMinWidth.value);
      });
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

  const { activeIndex } = useMenuKeyboard(renderList, layoutRef, (value) => {
    handleChange(value);
  });

  onMounted(() => {
    contentMinWidth.value = layoutRef.value!.getBoundingClientRect().width;
  });
</script>
<style lang="less">
  .bk-quick-search-type-mult-select {
    padding-bottom: 8px;
  }
</style>
