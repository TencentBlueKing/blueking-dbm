<template>
  <div
    ref="root"
    class="db-ticket-info-list">
    <slot />
  </div>
</template>
<script lang="ts">
  import Item from './InfoItem.vue';
  import useMaxWidth from './useMaxWidth';

  export { Item };
  export default {};
</script>
<script lang="ts" setup>
  const rootRef = useTemplateRef('root');

  useMaxWidth(rootRef);
</script>
<style lang="less">
  .db-ticket-info-list {
    display: flex;
    flex-wrap: wrap;
  }
</style>
