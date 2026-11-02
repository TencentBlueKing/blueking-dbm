<template>
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('回档：支持构造回档、库表闪回、记录级闪回。')" />
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
          <BkRadioButton label="ROLLBACK_FLASHBACK">
            {{ t('构造回档') }}
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
  import { useRouter } from 'vue-router';

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

  const flashbackType = ref<'RECORD_FLASHBACK' | 'TABLE_FLASHBACK'>(
    (route.query.type as keyof typeof comMap) || 'TABLE_FLASHBACK',
  );
  // 当前展示的闪回类型：选项随点击先变，确认可以离开后才切换内容
  const renderType = ref(flashbackType.value);

  useTicketDetail<Mysql.FlashBack>(TicketTypes.MYSQL_FLASHBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      flashbackType.value = details.flashback_type;
      renderType.value = details.flashback_type;
    },
  });

  // 选项还原为当前展示的类型（离开确认被取消、跳转失败时）
  const rollbackFlashbackType = () => {
    flashbackType.value = renderType.value;
  };

  const handleFlashbackTypeChange = (type: string) => {
    if (type === 'ROLLBACK_FLASHBACK') {
      switchSiblingRoute(
        () =>
          router.push({
            name: TicketTypes.MYSQL_ROLLBACK,
          }),
        rollbackFlashbackType,
      );
      return;
    }
    /**
     * 库表闪回 / 记录级闪回是同一路由只改 query，路由守卫不拦截；切换会卸载当前闪回表单，
     * 这里先做离开确认，确认后才切换展示内容，取消时选项还原、已填内容保留
     */
    leaveConfirm()
      .then(() => {
        renderType.value = type as keyof typeof comMap;
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
