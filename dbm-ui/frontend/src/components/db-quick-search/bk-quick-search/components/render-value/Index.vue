<template>
  <ValueTag
    :class="{
      'is-custom-input': isFocused && isCustomInput,
    }"
    :focused="isFocused"
    role="search-value"
    @edit="handleFocus"
    @remove="handleRemove">
    {{ value.name }}
    <template
      v-if="isFocused && currentDataConfig"
      #edit>
      <TagEdit
        :config="currentDataConfig!"
        :last-value="value"
        :last-value-text="lastValueText"
        @change="handleChange"
        @error="handleEditError" />
    </template>
    <template
      v-else
      #value>
      {{ lastValueText }}
    </template>
  </ValueTag>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref } from 'vue';

  import ValueTag from '@components/db-quick-search/bk-quick-search/components/ValueTag.vue';
  import type { IValue, Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { calcNeedShowValueMenu, getValuesText } from '@components/db-quick-search/bk-quick-search/utils';

  import TagEdit from './components/TagEdit.vue';

  interface Props {
    data: ContextProps['data'];
    value: IValue;
  }
  interface Emits {
    (e: 'remove'): void;
    (e: 'change', value: IValue): void;
    (e: 'error', message: string): void;
    (e: 'focus', message: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isFocused = ref(false);

  // 搜索项配置可能被外部移除，此时 tag 只支持删除，不进入编辑态
  const currentDataConfig = computed(() => _.find(props.data, (item) => item.id === props.value.id));
  const isCustomInput = computed(() => !calcNeedShowValueMenu(currentDataConfig.value));
  const lastValueText = computed(() => getValuesText(props.value.values, currentDataConfig.value));

  const handleRemove = () => {
    emits('remove');
  };

  const handleEditError = (message: string) => {
    emits('error', message);
  };

  const handleChange = (value: IValue) => {
    // TagEdit 组件在销毁时内部的 textarea 组件会触发 blur 事件，导致触发两次事件
    if (!isFocused.value) {
      return;
    }
    isFocused.value = false;
    if (value.values.length < 1) {
      emits('remove');
      return;
    }
    // 退出编辑时值没有变化，不触发搜索
    if (_.isEqual(value.values, props.value.values)) {
      return;
    }
    emits('change', value);
  };

  const handleFocus = () => {
    if (isFocused.value || !currentDataConfig.value) {
      return;
    }
    isFocused.value = true;
  };
</script>
