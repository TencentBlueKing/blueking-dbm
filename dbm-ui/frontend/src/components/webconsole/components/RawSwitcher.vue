<template>
  <div class="operate-item">
    <div class="operate-item-switcher">
      <BkSwitcher
        v-model="isRawMode"
        v-bk-tooltips="{
          content: t('开启后可正常显示中文'),
          disabled: isRawMode,
        }"
        theme="primary"
        @change="handleRawSwitch" />
      <span class="operate-title ml-5">{{ t('Raw 模式') }}</span>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'change', value: boolean): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isRawMode = ref(false);

  const handleRawSwitch = (value: boolean) => {
    emits('change', value);
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
