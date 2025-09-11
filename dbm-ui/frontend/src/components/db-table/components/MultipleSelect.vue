<template>
  <div :style="{ width: contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
    <div class="t-table__filter-pop-search">
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
        ref="wrapper"
        class="t-table__filter-pop-wrapper">
        <CheckboxGroup
          v-model="localValue"
          @change="handleChange">
          <div
            v-for="item in renderList"
            :key="item.label"
            class="t-table__filter-pop-item">
            <Checkbox
              :label="item.label"
              style="display: flex; flex: 1; flex-wrap: nowrap; white-space: nowrap"
              :value="item.value" />
          </div>
        </CheckboxGroup>
      </div>
    </BkLoading>
    <div
      v-if="filterKey && renderList.length < 1"
      class="t-table__filter-pop-search-empty">
      未搜索到 "{{ filterKey }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Checkbox, CheckboxGroup, Input } from 'tdesign-vue-next';
  import { nextTick, ref, shallowRef, useTemplateRef, watch } from 'vue';

  import { makeMap } from '@utils';

  import useMenuList from './hooks/useMenuList';

  interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    list?: {
      label: string;
      value: number | string;
    }[];

    remoteMethod?: (params: {
      defaultValue?: string;
      keyword?: string;
    }) => Promise<{ label: string; value: number | string }[]>;
    // eslint-disable-next-line vue/no-unused-properties
    remoteSearch?: boolean;
    value?: (number | string)[];
  }

  type Emits = (e: 'change', value: NonNullable<Props['list']>[number]['value'][]) => void;

  defineOptions({
    inheritAttrs: false,
  });

  const props = withDefaults(defineProps<Props>(), {
    list: () => [],
    remoteMethod: undefined,
    remoteSearch: false,
    value: () => [],
  });
  const emits = defineEmits<Emits>();

  const {
    filterKey,
    list,
    loading: isRemoteListLoading,
  } = useMenuList<{ label: string; value: number | string }>(props);

  const defaultValue = shallowRef<{ label: string; value: number | string }[]>([]);

  const wrapperRef = useTemplateRef('wrapper');
  const localValue = shallowRef(props.value);
  const contentMinWidth = ref(0);

  const renderList = computed(() => {
    const keyword = `${filterKey.value || ''}`.trim().toLowerCase();
    if (!keyword) {
      const modelValueMap = makeMap(defaultValue.value.map((item) => item.value));
      return [...defaultValue.value, ..._.filter(list.value, (item) => !modelValueMap[item.value])];
    }

    return _.filter(list.value, (item) => item.label.toLowerCase().includes(keyword));
  });

  watch(filterKey, () => {
    nextTick(() => {
      contentMinWidth.value = Math.max(wrapperRef.value!.getBoundingClientRect().width, contentMinWidth.value);
    });
  });

  watch(
    () => props.value,
    () => {
      if (defaultValue.value.length > 0) {
        return;
      }
      if (props.value.length > 0 && _.isFunction(props.remoteMethod)) {
        props.remoteMethod!({
          defaultValue: props.value.join(','),
        }).then((data) => {
          defaultValue.value = data;
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: any) => {
    emits('change', value);
  };
</script>
