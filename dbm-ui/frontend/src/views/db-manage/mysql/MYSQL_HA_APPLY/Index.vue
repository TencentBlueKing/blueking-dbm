<template>
  <Apply />
</template>
<script setup lang="ts">
  import { useRoute, useRouter } from 'vue-router';

  import Apply from '@views/db-manage/mysql/common/apply/Index.vue';

  const route = useRoute();
  const router = useRouter();

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.back();
        return;
      }
      router.push({
        name: route.query.from as string,
      });
    },
  });
</script>
