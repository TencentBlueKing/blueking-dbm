<template>
  <RouterView />
  <DbaHelper
    v-if="!isPlatformIndex"
    :biz-id="bizId" />
</template>

<script setup lang="ts">
  import { provide, ref } from 'vue';

  import DbaHelper from '@views/db-manage/common/DbaHelper.vue';

  import { serviceApplyKey } from './const';

  const route = useRoute();
  const isPlatformIndex = computed(() =>
    ['BussinessServiceApplyIndex', 'serviceApplyIndex'].includes(route.name as string),
  );

  watch(
    () => route.name,
    () => {
      bizId.value = 0;
    },
  );

  const bizId = ref<number>(0);

  const changeBizId = (id: number) => {
    bizId.value = Number(id);
  };

  provide(serviceApplyKey, { changeBizId });
</script>
