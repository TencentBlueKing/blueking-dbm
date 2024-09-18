<template>
  <Component
    :is="renderCom"
    v-bind="attrs" />
</template>
<script setup lang="ts">
  import { useAttrs } from 'vue';

  import { useStretchLayout } from '@hooks';

  import CardMode from './components/CardMode.vue';
  import TableMode from './components/TableMode.vue';

  const attrs = useAttrs();

  const { isSplited: isStretchLayoutOpen } = useStretchLayout();

  const renderCom = computed(() => (isStretchLayoutOpen.value ? CardMode : TableMode));
</script>
