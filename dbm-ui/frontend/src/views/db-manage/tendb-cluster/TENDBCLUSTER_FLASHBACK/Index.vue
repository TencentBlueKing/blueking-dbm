<template>
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      theme="info"
      :title="t('闪回：通过 flashback 工具，对 row 格式的 binlog 做逆向操作')" />
    <BkForm
      ref="formRef"
      class="mb-24 toolbox-form"
      form-type="vertical">
      <BkFormItem
        :label="t('时区')"
        required>
        <TimeZonePicker style="width: 450px" />
      </BkFormItem>
      <BkFormItem
        :label="t('闪回方式')"
        required>
        <BkRadioGroup v-model="flashbackType">
          <BkRadioButton
            label="TABLE_FLASHBACK"
            style="width: 225px">
            {{ t('库表闪回') }}
          </BkRadioButton>
          <BkRadioButton
            label="RECORD_FLASHBACK"
            style="width: 225px">
            {{ t('记录级闪回') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <Component :is="comMap[flashbackType]" />
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { type TendbCluster } from '@services/model/ticket/ticket';
  import { useTicketDetail } from '@hooks';
  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import RECORD_FLASHBACK from './RECORD_FLASHBACK/Index.vue';
  import TABLE_FLASHBACK from './TABLE_FLASHBACK/Index.vue';

  const comMap = {
    TABLE_FLASHBACK,
    RECORD_FLASHBACK,
  };

  const { t } = useI18n();
  const route = useRoute();

  const flashbackType = ref<'RECORD_FLASHBACK' | 'TABLE_FLASHBACK'>(
    (route.params.type as keyof typeof comMap) || 'TABLE_FLASHBACK',
  );

  useTicketDetail<TendbCluster.FlashBack>(TicketTypes.TENDBCLUSTER_FLASHBACK, {
    onSuccess(ticketDetails) {
      const { details } = ticketDetails;
      flashbackType.value = details.flashback_type;
    },
  });
</script>
