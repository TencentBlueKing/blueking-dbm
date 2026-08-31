<template>
  <div :style="{ width: contentMinWidth > 0 ? `${contentMinWidth + 12}px` : '' }">
    <div class="t-table__filter-pop-search">
      <Input
        v-model="serachKey"
        borderless
        clearable
        :placeholder="t('请输入关键字')">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
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
            :value="item.value" />
        </div>
      </CheckboxGroup>
    </div>

    <div
      v-if="serachKey && renderList.length < 1"
      class="t-table__filter-pop-search-empty">
      {{ t('搜索为空') }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Checkbox, CheckboxGroup, Input } from 'tdesign-vue-next';
  import { nextTick, onMounted, ref, shallowRef, useTemplateRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  type Emits = (e: 'change', value: Props['list'][number]['value'][]) => void;

  interface Props {
    list: {
      label: string;
      value: boolean | number | string;
    }[];
    value?: (boolean | number | string)[];
  }

  defineOptions({
    inheritAttrs: false,
  });
  const props = withDefaults(defineProps<Props>(), {
    value: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const wrapperRef = useTemplateRef('wrapper');
  const serachKey = ref('');
  const renderList = shallowRef([...props.list]);
  const localValue = shallowRef(props.value);
  const contentMinWidth = ref(0);

  watch(
    () => [serachKey.value, props.list],
    () => {
      if (!serachKey.value.trim()) {
        renderList.value = [...props.list];
        return;
      }
      renderList.value = props.list.filter((item) =>
        item.label.toLocaleLowerCase().includes(serachKey.value.toLocaleLowerCase()),
      );
    },
    {
      immediate: true,
    },
  );
  watch(
    () => props.list,
    () => {
      nextTick(() => {
        contentMinWidth.value = Math.max(wrapperRef.value!.getBoundingClientRect().width, contentMinWidth.value);
      });
    },
  );

  const handleChange = (value: Props['list'][number]['value'][]) => {
    emits('change', value);
  };

  onMounted(() => {
    contentMinWidth.value = wrapperRef.value!.getBoundingClientRect().width;
  });
</script>
