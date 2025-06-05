<template>
  <BkTagInput
    v-model="modelValue"
    v-bind="{ ...attrs, ...props }"
    allow-auto-match
    allow-create
    clearable
    has-delete-icon
    :max-data="single ? 1 : -1"
    :paste-fn="tagInputPasteFn" />
</template>
<script setup lang="ts">
  import { batchSplitRegex } from '@common/regex';

  export interface Props {
    single?: boolean;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string[]>({});

  const attrs = useAttrs();

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));
</script>
