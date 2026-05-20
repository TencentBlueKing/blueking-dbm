<template>
  <BkSelect
    v-model="localValue"
    :clearable="false"
    @change="handleChange">
    <BkOptionGroup group-style="divider">
      <BkOption
        v-for="item in resourceDbTypes"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </BkOptionGroup>
    <BkOptionGroup group-style="divider">
      <BkOption
        :label="specialOptionLabelMap[SpecialOptions.PUBLIC]"
        :value="SpecialOptions.PUBLIC" />
    </BkOptionGroup>
  </BkSelect>
</template>

<script setup lang="ts">
  import { DBTypes, resourceDbTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';

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
