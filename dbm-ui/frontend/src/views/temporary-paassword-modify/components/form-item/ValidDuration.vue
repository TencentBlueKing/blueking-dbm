<template>
  <BkFormItem
    :label="t('有效时长')"
    property="validDuration"
    required>
    <div class="valid-duration">
      <BkInput
        v-model="modelValue"
        class="valid-duration-input"
        :clearable="false"
        :min="1"
        :precision="0"
        type="number" />
      <DbSelect
        v-model="validDurationType"
        class="valid-duration-type"
        :clearable="false">
        <DbOption
          v-for="item in validDurationList"
          :key="item.value"
          :label="item.label"
          :value="item.value" />
      </DbSelect>
    </div>
    <div class="anticipated-effective-time">{{ t('预计失效时间') }}：{{ anticipatedEffectiveTime }}</div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<number>();

  const validDurationType = defineModel<string>('validDurationType');

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

  const anticipatedEffectiveTime = computed(() => {
    const currentDate = dayjs();
    const hours =
      validDurationType.value === VALID_DURATION_TYPE.DAY ? Number(modelValue.value) * 24 : Number(modelValue.value);

    return currentDate.add(hours, 'hour').format('YYYY-MM-DD HH:mm');
  });
</script>
<style scoped lang="less">
  .valid-duration {
    display: flex;

    .valid-duration-input {
      width: 300px;
      border-right: none;
      border-radius: 2px 0 0 2px;
    }

    .valid-duration-type {
      width: 88px;

      :deep(.dbm-select-input-box) {
        border-radius: 0 2px 2px 0;
      }
    }
  }

  .anticipated-effective-time {
    margin-top: 8px;
    font-size: 12px;
    line-height: 12px;
  }
</style>
