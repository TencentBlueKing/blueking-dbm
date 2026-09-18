<template>
  <DbTagInput
    v-model="modelValue"
    v-bind="{ ...attrs, ...props }"
    allow-create
    clearable
    :multiple="!single"
    :split-fn="tagInputSplitFn" />
</template>
<script setup lang="ts">
  import { batchSplitRegex } from '@common/regex';

  export interface Props {
    single?: boolean;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string[]>({});

  const attrs = useAttrs();

  const tagInputSplitFn = (value: string) => value.split(batchSplitRegex);
</script>
