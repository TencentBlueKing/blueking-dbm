<template>
  <BkUserSelector
    v-model="modelValue"
    :api-base-url="apiBaseUrl"
    draggable
    multiple
    :tenant-id="tenantId" />
</template>

<script setup lang="ts">
  import urlJoin from 'url-join';

  import BkUserSelector from '@blueking/bk-user-selector';

  import { useSystemEnviron, useUserProfile } from '@stores';

  import '@blueking/bk-user-selector/vue3/vue3.css';

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const systemEnvironStore = useSystemEnviron();
  const { tenantId } = useUserProfile();

  const apiBaseUrl = urlJoin(systemEnvironStore.urls.USER_MANAGE_FRONTEND_APIGW_DOMAIN);
</script>
