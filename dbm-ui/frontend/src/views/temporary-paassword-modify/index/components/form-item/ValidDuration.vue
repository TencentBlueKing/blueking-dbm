<template>
  <BkFormItem
    :label="t('有效时长')"
    property="validDuration"
    required>
    <BkComposeFormItem>
      <BkInput
        v-model="modelValue"
        :clearable="false"
        :min="1"
        :precision="0"
        style="width: 300px"
        type="number" />
      <BkSelect
        v-model="validDurationType"
        :clearable="false"
        style="width: 88px">
        <BkOption
          v-for="item in validDurationList"
          :key="item.value"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
    </BkComposeFormItem>
    <div class="anticipated-effective-time">{{ t('预计失效时间') }}：{{ anticipatedEffectiveTime }}</div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const VALID_DURATION_TYPE = {
    DAY: 'day',
    HOUR: 'hour',
  };

  const validDurationList = [
    {
      label: t('天'),
      value: VALID_DURATION_TYPE.DAY,
    },
    {
      label: t('小时'),
      value: VALID_DURATION_TYPE.HOUR,
    },
  ];

  const modelValue = defineModel<number>();
  const validDurationType = defineModel<string>('validDurationType');

  const anticipatedEffectiveTime = computed(() => {
    const currentDate = dayjs();
    const hours =
      validDurationType.value === VALID_DURATION_TYPE.DAY ? Number(modelValue.value) * 24 : Number(modelValue.value);

    return currentDate.add(hours, 'hour').format('YYYY-MM-DD HH:mm');
  });
</script>
<style scoped lang="less">
  .anticipated-effective-time {
    font-size: 12px;
    line-height: 12px;
  }
</style>
