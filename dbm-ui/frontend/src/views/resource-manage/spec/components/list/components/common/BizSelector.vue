<template>
  <BkTagInput
    v-model="modelValue"
    collapse-tags
    has-delete-icon
    :list="bizList"
    v-bind="attrs"
    :paste-fn="tagInputPasteFn"
    style="flex: 1"
    trigger="focus"
    @change="handleChange" />
</template>

<script setup lang="ts">
  import { batchSplitRegex } from '@common/regex';

  import { useGlobalBizs } from '@/stores';

  type Emits = (e: 'change') => void;

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string[]>();

  const attrs = useAttrs();

  const { bizs } = useGlobalBizs();

  const bizList = bizs.map((item) => ({
    id: `${item.bk_biz_id}`,
    name: item.name,
  }));
  const bizNameMap = Object.fromEntries(bizList.map((item) => [item.name, item.id]));

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: bizNameMap[item] }));

  const handleChange = () => {
    emits('change');
  };
</script>
