<template>
  <BkUserSelector
    v-bind="$attrs"
    v-model="selectedValue"
    :api-base-url="apiBaseUrl"
    draggable
    :multiple="multiple"
    :tenant-id="tenantId"
    @change="handleUsersChange" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import urlJoin from 'url-join';

  import BkUserSelector from '@blueking/bk-user-selector';
  import type { FormattedUser } from '@blueking/bk-user-selector/typings/types';

  import { useSystemEnviron, useUserProfile } from '@stores';

  import '@blueking/bk-user-selector/vue3/vue3.css';

  interface Props {
    multiple?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    multiple: true,
  });
  const modelValue = defineModel<string[]>({
    required: true,
  });

  const systemEnvironStore = useSystemEnviron();
  const { tenantId } = useUserProfile();

  const apiBaseUrl = urlJoin(systemEnvironStore.urls.USER_MANAGE_FRONTEND_APIGW_DOMAIN);

  const selectedValue = ref<string | string[]>(props.multiple ? [] : '');

  watch(
    modelValue,
    (newValue, oldValue) => {
      if (_.isEqual(newValue, oldValue)) {
        return;
      }

      if (props.multiple) {
        selectedValue.value = newValue;
      } else {
        selectedValue.value = newValue[0] || '';
      }
    },
    {
      immediate: true,
    },
  );

  const handleUsersChange = (users: FormattedUser | FormattedUser[] | null) => {
    if (users) {
      if (props.multiple) {
        modelValue.value = (users as FormattedUser[]).map((user) => user.id);
      } else {
        modelValue.value = [(users as FormattedUser).id];
      }
    }
  };
</script>
