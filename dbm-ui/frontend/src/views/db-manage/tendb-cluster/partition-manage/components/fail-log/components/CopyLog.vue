<template>
  <div
    class="copy-log-icon"
    @click="handleCopy">
    <DbIcon type="copy" />
  </div>
</template>
<script lang="ts" setup>
  import { execCopy } from '@utils';

  interface Props {
    content: string;
  }

  const props = defineProps<Props>();

  const handleCopy = () => {
    execCopy(props.content);
  };
</script>
<style lang="less" scoped>
  .copy-log-icon {
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
