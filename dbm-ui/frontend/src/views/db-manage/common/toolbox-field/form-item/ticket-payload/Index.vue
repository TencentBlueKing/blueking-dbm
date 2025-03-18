<template>
  <BkFormItem :label="t('备注')">
    <BkInput
      v-model="modelValue.remark"
      :maxlength="500"
      :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
      style="width: 700px"
      type="textarea" />
  </BkFormItem>
</template>
<script lang="ts">
  interface TicketItem {
    remark: string;
  }
  export const createTickePayload = (data = {} as TicketItem) => ({
    remark: data.remark || '',
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<TicketItem>({
    required: true,
  });

  const { t } = useI18n();
</script>
