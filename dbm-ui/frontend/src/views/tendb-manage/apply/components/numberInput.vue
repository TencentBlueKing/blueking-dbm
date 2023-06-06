<template class="number-input">
  <BkInput
    :min="1"
    :model-value="modelValue"
    type="number"
    v-bind="$attrs"
    @change="handleChange">
    <template #prefix>
      <span
        class="count-icon prefix"
        @click="handleSub()">－</span>
    </template>
    <template #suffix>
      <div
        class="count-icon suffix"
        @click="handleAdd()">
        +
      </div>
    </template>
  </BkInput>
</template>
<script setup lang="ts">
  interface Props {
    modelValue: number,
  }
  interface Emits {
    (e: 'update:modelValue', value: number): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const handleSub = () => {
    if (props.modelValue <= 1) {
      emits('update:modelValue', 1);
      return;
    }
    emits('update:modelValue', props.modelValue - 1);
  };
  const handleAdd = () => {
    emits('update:modelValue', props.modelValue + 1);
  };
  const handleChange = (value: any) => {
    emits('update:modelValue', value);
  };
</script>
<style lang="less" scoped>
  :deep(.bk-input--number-control){
    display: none;
  }
  .count-icon {
      width: 24px;
      height: 24px;
      text-align: center;
      color: #9b9fa8;
      display: block;
      background-color: #F5F7FA;
      border-radius: 1px;
      line-height: 22px;
      cursor: pointer;
  }
  .prefix {
    font-size: 24px;
    margin: 3px 0 3px 3px;
  }
  .prefix:hover {
    background-color: #eaebf0;
  }
  .suffix {
    font-size: 18px;
    margin: 3px 3px 3px 0;
  }
  .suffix:hover {
    background-color: #eaebf0;
  }
</style>
