<template>
  <div class="operate-item">
    <div class="operate-item-switcher">
      <BkSwitcher
        v-model="modelValue"
        v-bk-tooltips="{
          content: t('开启后可正常显示中文'),
          disabled: modelValue,
        }"
        size="small"
        theme="primary"
        @change="handleRawSwitch" />
      <span class="operate-title ml-5">{{ t('Raw 模式') }}</span>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<boolean | undefined>({
    default: undefined,
  });

  const handleRawSwitch = (value: boolean) => {
    modelValue.value = value;
  };
</script>

<style lang="less" scoped>
  .operate-item-switcher {
    display: flex;
    height: 28px;
    padding: 0 6px;
    align-items: center;
    justify-content: center;
  }
</style>
