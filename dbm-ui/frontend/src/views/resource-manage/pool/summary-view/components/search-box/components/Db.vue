<template>
  <BkSelect
    v-model="modelValue"
    :clearable="false"
    @change="handleChange">
    <BkOption
      v-for="dbType in DBTypes"
      :key="dbType"
      :label="dbType"
      :value="dbType" />
  </BkSelect>
</template>

<script setup lang="ts">
  import { DBTypes } from '@common/const';

  interface Emits {
    (e: 'change', value: DBTypes): void;
  }

  interface Exposes {
    getValue: () => {
      db_type: DBTypes;
    };
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<DBTypes>({
    required: true,
    default: DBTypes.MYSQL,
  });

  const handleChange = (value: DBTypes) => {
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue: () => ({
      db_type: modelValue.value,
    }),
  });
</script>
