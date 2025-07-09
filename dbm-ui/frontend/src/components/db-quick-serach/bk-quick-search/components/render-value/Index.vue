<template>
  <ValueTag
    :class="{
      'is-custom-input': isFocused && isCustomInput,
      'is-single-input': isFocused && !isReadonly,
    }"
    :focued="isFocused"
    role="search-value"
    @edit="handleFoucs"
    @remove="handleRemove">
    {{ value.name }}
    <template
      v-if="isFocused"
      #edit>
      <TagEdit
        :config="currentDataConfig"
        :last-value="value"
        :last-value-text="lastValueText"
        :readonly="isReadonly"
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

  import ValueTag from '@components/db-quick-serach/bk-quick-search/components/ValueTag.vue';
  import { comType } from '@components/db-quick-serach/bk-quick-search/constants';
  import type { IValue, Props as ContextProps } from '@components/db-quick-serach/bk-quick-search/Index.vue';

  import { calcNeedShowValueMenu, getValuesText } from '@/components/db-quick-serach/bk-quick-search/utils';

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

  const currentDataConfig = _.find(props.data, (item) => item.id === props.value.id) as Props['data'][number];
  const isCustomInput = !calcNeedShowValueMenu(currentDataConfig);
  const isReadonly = Boolean(
    currentDataConfig.type &&
      [comType.DATE, comType.DATETIME, comType.DATETIME_RANGE, comType.DATETIME_RANGE].includes(
        currentDataConfig.type as comType,
      ),
  );

  const isFocused = ref(false);
  const lastValueText = computed(() => getValuesText(props.value.values, currentDataConfig));

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
    } else {
      emits('change', value);
    }
  };

  const handleFoucs = () => {
    if (isFocused.value) {
      return;
    }
    isFocused.value = true;
  };
</script>
