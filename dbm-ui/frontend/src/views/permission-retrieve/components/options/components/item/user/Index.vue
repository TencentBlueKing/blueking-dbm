<template>
  <BkFormItem
    :label="t('账号')"
    property="users"
    required>
    <UserSelect
      ref="userSelectRef"
      v-model="modelValue" />
  </BkFormItem>
</template>

<script setup lang="tsx">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import UserSelect from './components/UserSelect.vue';

  interface Expose {
    getUserList: ComponentExposed<typeof UserSelect>['getUserList'];
  }

  const { t } = useI18n();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const userSelectRef = ref<ComponentExposed<typeof UserSelect>>();

  defineExpose<Expose>({
    getUserList(params: Parameters<Expose['getUserList']>[number]) {
      userSelectRef.value!.getUserList(params);
    },
  });
</script>
