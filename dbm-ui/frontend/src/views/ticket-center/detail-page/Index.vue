<template>
  <Detail :ticket-id="ticketId" />
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import Detail from '@views/ticket-center/common/ticket-detail/Index.vue';

  const route = useRoute();

  const ticketId = computed(() => Number(route.params.ticketId) || 0);
</script>
