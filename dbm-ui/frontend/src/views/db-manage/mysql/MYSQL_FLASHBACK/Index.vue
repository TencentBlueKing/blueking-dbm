<template>
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('回档：按备份记录或指定时间恢复数据，支持新机构造、原地构造、库表闪回与记录级闪回。')" />
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
          <BkRadioButton label="BUILD_INTO_NEW_CLUSTER">
            {{ t('新机构造回档') }}
          </BkRadioButton>
          <BkRadioButton label="ROLLBACK_FLASHBACK">
            {{ t('原地构造回档') }}
          </BkRadioButton>
          <BkRadioButton label="TABLE_FLASHBACK">
            {{ t('库表闪回回档') }}
          </BkRadioButton>
          <BkRadioButton label="RECORD_FLASHBACK">
            {{ t('记录级闪回回档') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <Component :is="comMap[renderType]" />
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type Mysql } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import { leaveConfirm, switchSiblingRoute } from '@utils';

  import RECORD_FLASHBACK from './RECORD_FLASHBACK/Index.vue';
  import TABLE_FLASHBACK from './TABLE_FLASHBACK/Index.vue';

  const comMap = {
    RECORD_FLASHBACK,
    TABLE_FLASHBACK,
  };

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const renderType = ref<keyof typeof comMap>(
    route.query.type === 'RECORD_FLASHBACK' ? 'RECORD_FLASHBACK' : 'TABLE_FLASHBACK',
  );
  const flashbackType = ref<string>(renderType.value);

  // 取消切换时恢复选项，保留当前表单
  const rollbackFlashbackType = () => {
    flashbackType.value = renderType.value;
  };

  useTicketDetail<Mysql.FlashBack>(TicketTypes.MYSQL_FLASHBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      renderType.value = details.flashback_type;
      flashbackType.value = details.flashback_type;
    },
  });

  const handleFlashbackTypeChange = (type: string) => {
    if (type === 'BUILD_INTO_NEW_CLUSTER' || type === 'ROLLBACK_FLASHBACK') {
      switchSiblingRoute(
        () =>
          router.push({
            name: type === 'BUILD_INTO_NEW_CLUSTER' ? TicketTypes.MYSQL_ROLLBACK_NEW_HOST : TicketTypes.MYSQL_ROLLBACK,
          }),
        rollbackFlashbackType,
      );
      return;
    }
    if ((type !== 'TABLE_FLASHBACK' && type !== 'RECORD_FLASHBACK') || type === renderType.value) {
      return;
    }
    // 同页切换先确认，取消时保留表单并恢复选项
    leaveConfirm()
      .then(() => {
        renderType.value = type;
        router.push({
          name: TicketTypes.MYSQL_FLASHBACK,
          query: {
            type,
          },
        });
      })
      .catch(rollbackFlashbackType);
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
