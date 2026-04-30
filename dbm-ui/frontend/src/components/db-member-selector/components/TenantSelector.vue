<template>
  <BkUserSelector
    v-bind="$attrs"
    v-model="modelValue"
    :api-base-url="apiBaseUrl"
    draggable
    :multiple="multiple"
    :tenant-id="tenantId" />
</template>

<script setup lang="ts">
  import urlJoin from 'url-join';

  import BkUserSelector from '@blueking/bk-user-selector';

  import { useSystemEnviron, useUserProfile } from '@stores';

  import '@blueking/bk-user-selector/vue3/vue3.css';

  interface Props {
    multiple?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    multiple: true,
  });
  const modelValue = defineModel<string[]>({
    required: true,
  });

  const systemEnvironStore = useSystemEnviron();
  const { tenantId } = useUserProfile();

  const apiBaseUrl = urlJoin(systemEnvironStore.urls.USER_MANAGE_FRONTEND_APIGW_DOMAIN);
</script>
