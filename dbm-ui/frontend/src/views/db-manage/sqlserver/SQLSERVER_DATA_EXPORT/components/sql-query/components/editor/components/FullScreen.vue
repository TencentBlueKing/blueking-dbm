<template>
  <div
    class="fullscreen-icon"
    @click="handleClickFullScreen">
    <DbIcon
      class="fullscreen-icon"
      :type="modelValue ? 'un-full-screen' : 'full-screen'" />
  </div>
</template>
<script lang="ts" setup>
  type Emits = (e: 'change') => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<boolean>({
    default: false,
  });

  const handleClickFullScreen = () => {
    modelValue.value = !modelValue.value;
    emits('change');
  };
</script>
<style lang="less" scoped>
  .fullscreen-icon {
    display: flex;
    width: 28px;
    height: 28px;
    color: #c4c6cc;
    border-radius: 2px;
    justify-content: center;
    align-items: center;

    &:hover {
      background: #424242;
    }
  }
</style>
