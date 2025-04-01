<template>
  <Detail
    class="ticket-details-page"
    :ticket-id="ticketId" />
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import Detail from '@views/ticket-center/common/ticket-detail/Index.vue';

  const route = useRoute();

  const ticketId = computed(() => Number(route.params.ticketId) || 0);
</script>
<style lang="less">
  .ticket-details-page {
    padding: 24px;
    font-size: 12px;
    background: #f5f7fa;
  }
</style>
