<template>
  <BkUserSelector
    v-model="modelValue"
    :api-base-url="apiBaseUrl"
    draggable
    multiple
    :tenant-id="tenantId" />
</template>

<script setup lang="ts">
  import BkUserSelector from '@blueking/bk-user-selector';

  import { useUserProfile } from '@stores';

  import '@blueking/bk-user-selector/vue3/vue3.css';

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { tenantId } = useUserProfile();

  const apiBaseUrl = 'https://bk-user-web.apigw.o.woa.com/prod';
</script>
