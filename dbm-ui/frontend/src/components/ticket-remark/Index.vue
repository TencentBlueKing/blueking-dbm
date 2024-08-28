<template>
  <DbForm
    class="toolbox-form mt-24"
    form-type="vertical">
    <BkFormItem :label="t('备注')">
      <BkInput
        v-model="modelValue"
        :maxlength="500"
        :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
        style="width: 700px"
        type="textarea" />
    </BkFormItem>
  </DbForm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<string>();
</script>
