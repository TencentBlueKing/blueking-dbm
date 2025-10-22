<template>
  <BkCheckboxGroup
    v-model="localValue"
    class="notify-channel-checkbox-group"
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
      <DbIcon
        class="channel-icon"
        :class="item.customClass"
        :svg="item.isSvg"
        :type="item.icon" />
      <span>{{ item.label }}</span>
    </BkCheckbox>
  </BkCheckboxGroup>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const emits = defineEmits<Emits>();

  const localValue = defineModel<string[]>({ default: [] });

  type Emits = (e: 'change', value: string[]) => void;

  const { t } = useI18n();

  const chooseList = [
    {
      customClass: 'qiwei',
      icon: 'qw',
      isSvg: true,
      label: t('企业微信'),
      value: 'weixin',
    },
    {
      customClass: 'email',
      icon: 'youjian',
      isSvg: false,
      label: t('邮件'),
      value: 'mail',
    },
    {
      customClass: 'duanxin',
      icon: 'duanxin',
      isSvg: false,
      label: t('短信'),
      value: 'sms',
    },
  ];

  const handleChange = (value: string[]) => {
    emits('change', value);
  };
</script>
<style lang="less">
  .notify-channel-checkbox-group {
    .bk-checkbox {
      margin-left: 0;

      .bk-checkbox-label {
        display: flex;
        align-items: center;
        width: 128px;

        .channel-icon {
          margin-right: 5px;

          &.qiwei {
            font-size: 16px;
          }

          &.email {
            font-size: 15px;
            color: #f59500;
          }

          &.duanxin {
            font-size: 14px;
            color: #3a84ff;
          }
        }
      }
    }
  }
</style>
