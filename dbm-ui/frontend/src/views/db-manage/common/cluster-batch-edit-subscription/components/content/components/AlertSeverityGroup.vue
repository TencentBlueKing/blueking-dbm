<template>
  <BkCheckboxGroup
    v-model="localValue"
    class="alarm-level-checkbox-group"
    @change="handleChange">
    <BkCheckbox
      v-for="(item, index) in chooseList"
      :key="index"
      v-bk-tooltips="{
        content: t('至少保留一个选项'),
        disabled: localValue.length > 1 || localValue[0] !== item.value,
      }"
      :disabled="localValue.length === 1 && localValue[0] === item.value"
      :label="item.value">
      <span
        class="rect-shape"
        :class="item.customClass"></span>
      <span>{{ item.label }}</span>
    </BkCheckbox>
  </BkCheckboxGroup>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  type Emits = (e: 'change', value: number[]) => void;

  const emits = defineEmits<Emits>();

  const localValue = defineModel<number[]>({ default: [] });

  const { t } = useI18n();

  const chooseList = [
    {
      customClass: 'fatal',
      label: t('致命'),
      value: 1,
    },
    {
      customClass: 'warn',
      label: t('预警'),
      value: 2,
    },
    {
      customClass: 'info',
      label: t('提醒'),
      value: 3,
    },
  ];

  const handleChange = (value: number[]) => {
    emits('change', value);
  };
</script>
<style lang="less">
  .alarm-level-checkbox-group {
    .bk-checkbox {
      margin-left: 0;

      .bk-checkbox-label {
        display: flex;
        align-items: center;
        width: 128px;

        .rect-shape {
          display: inline-block;
          width: 8px;
          height: 8px;
          margin-right: 5px;

          &.fatal {
            background-color: #e71818;
          }

          &.warn {
            background-color: #f59500;
          }

          &.info {
            background-color: #3a84ff;
          }
        }
      }
    }
  }
</style>
