<template>
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('支持构造回档、库表闪回、记录级闪回')" />
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
        :label="t('回档类型')"
        required>
        <BkRadioGroup
          v-model="flashbackType"
          style="width: 450px"
          type="card"
          @change="handleFlashbackTypeChange">
          <!-- <BkRadioButton label="BUILD_INTO_METACLUSTER">
            {{ t('构造回档') }}
          </BkRadioButton> -->
          <BkRadioButton label="TABLE_FLASHBACK">
            {{ t('库表闪回回档') }}
          </BkRadioButton>
          <BkRadioButton label="RECORD_FLASHBACK">
            {{ t('记录级闪回回档') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <Component :is="comMap[flashbackType]" />
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { type Mysql } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import RECORD_FLASHBACK from './RECORD_FLASHBACK/Index.vue';
  import TABLE_FLASHBACK from './TABLE_FLASHBACK/Index.vue';

  const comMap = {
    RECORD_FLASHBACK,
    TABLE_FLASHBACK,
  };

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const flashbackType = ref<'RECORD_FLASHBACK' | 'TABLE_FLASHBACK'>(
    (route.query.type as keyof typeof comMap) || 'TABLE_FLASHBACK',
  );

  useTicketDetail<Mysql.FlashBack>(TicketTypes.MYSQL_FLASHBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      flashbackType.value = details.flashback_type;
    },
  });

  const handleFlashbackTypeChange = (type: string) => {
    if (['RECORD_FLASHBACK', 'TABLE_FLASHBACK'].includes(type)) {
      router.push({
        name: TicketTypes.MYSQL_FLASHBACK,
        query: {
          type,
        },
      });
    }
    // } else if (type === 'BUILD_INTO_METACLUSTER') {
    //   router.push({
    //     name: TicketTypes.MYSQL_ROLLBACK,
    //   });
    // }
  };
</script>
