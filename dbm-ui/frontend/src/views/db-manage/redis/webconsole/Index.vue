<template>
  <WebConsole :db-type="DBTypes.REDIS" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebConsole from '@views/db-manage/common/webconsole/Index.vue';

  const router = useRouter();

  defineExpose({
    routerBack() {
      router.push({
        name: 'RedisToolboxIndex',
      });
    },
  });
</script>
