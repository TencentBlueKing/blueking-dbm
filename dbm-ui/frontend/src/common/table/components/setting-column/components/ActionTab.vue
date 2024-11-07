<template>
  <div class="action-tab-wrapper">
    <div
      class="tab-item"
      :class="{ active: modelValue === 'field' }"
      @click="() => handleChange('field')">
      字段设置
    </div>
    <div
      class="tab-item"
      :class="{ active: modelValue === 'others' }"
      @click="() => handleChange('others')">
      高级设置
    </div>
  </div>
</template>
<script setup lang="ts">
  const modelValue = defineModel<string>({
    default: 'field',
  });

  const handleChange = (value: string) => {
    modelValue.value = value;
  };
</script>
