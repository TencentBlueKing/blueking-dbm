<template>
  <div class="db-ticket-info-list">
    <slot />
  </div>
</template>
<script lang="ts">
  import Item from './InfoItem.vue';

  export { Item };
  export default {};
</script>
<style lang="less">
  .db-ticket-info-list {
    display: flex;
    flex-wrap: wrap;
  }
</style>
