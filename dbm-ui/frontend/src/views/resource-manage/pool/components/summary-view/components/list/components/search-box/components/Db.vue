<template>
  <DbSelect
    v-model="localValue"
    :clearable="false"
    @change="handleChange">
    <DbOptionGroup group-style="divider">
      <DbOption
        v-for="item in readResourceDbTypes"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </DbOptionGroup>
    <DbOptionGroup group-style="divider">
      <DbOption
        :label="specialOptionLabelMap[SpecialOptions.PUBLIC]"
        :value="SpecialOptions.PUBLIC" />
    </DbOptionGroup>
  </DbSelect>
</template>

<script setup lang="ts">
  import { DBTypes, readResourceDbTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';

  interface Props {
    model: Record<string, string>;
  }

  type Emits = (e: 'change', value: { db_type: string }) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const localValue = ref<string>(DBTypes.REDIS);

  watch(
    () => props.model,
    () => {
      if (props.model.db_type) {
        localValue.value = props.model.db_type;
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change', {
      db_type: localValue.value,
    });
  };
</script>
