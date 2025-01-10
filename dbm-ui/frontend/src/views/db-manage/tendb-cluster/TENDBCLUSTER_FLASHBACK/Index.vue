<template>
  <div>
    <Component :is="com" />
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRoute } from 'vue-router';

  import Create from './Create.vue';
  import Successed from './Successed.vue';

  const route = useRoute();

  const comMap = {
    ticket: Create,
    success: Successed,
  };

  const page = ref('');

  const com = computed(() => {
    if (comMap[page.value as keyof typeof comMap]) {
      return comMap[page.value as keyof typeof comMap];
    }
    return Create;
  });

  watch(
    route,
    () => {
      page.value = route.params.page as string;
    },
    {
      immediate: true,
    },
  );
</script>
