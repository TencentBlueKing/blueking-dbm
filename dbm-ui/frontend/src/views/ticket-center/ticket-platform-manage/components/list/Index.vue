<template>
  <KeepAlive>
    <Component
      :is="renderCom"
      v-bind="attrs" />
  </KeepAlive>
</template>
<script setup lang="ts">
  import { computed, useAttrs } from 'vue';
  import { useRoute } from 'vue-router';

  import { useStretchLayout } from '@hooks';

  import CardMode from './components/CardMode.vue';
  import TableMode from './components/TableMode.vue';

  const attrs = useAttrs();

  const route = useRoute();
  const { isSplited } = useStretchLayout();

  const ticketId = computed(() => Number(route.params.ticketId) || 0);

  const renderCom = computed(() => {
    if (ticketId.value) {
      return CardMode;
    }
    return isSplited.value ? CardMode : TableMode;
  });
</script>
