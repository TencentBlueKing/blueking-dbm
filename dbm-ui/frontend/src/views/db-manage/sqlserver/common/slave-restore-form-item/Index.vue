<template>
  <BkFormItem
    :label="t('重建类型')"
    property="restoreType"
    required>
    <CardCheckbox
      v-model="modelValue"
      :desc="t('在原主机上进行故障从库实例重建')"
      icon="rebuild"
      :title="t('原地重建')"
      :true-value="TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE" />
    <CardCheckbox
      v-model="modelValue"
      class="ml-8"
      :desc="t('将从库主机的全部实例重建到新主机')"
      icon="host"
      :title="t('新机重建')"
      :true-value="TicketTypes.SQLSERVER_RESTORE_SLAVE" />
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  const modelValue = defineModel<string>({
    required: true,
  });
  const { t } = useI18n();
  const router = useRouter();

  watch(modelValue, () => {
    router.push({
      name: modelValue.value,
    });
  });
</script>
