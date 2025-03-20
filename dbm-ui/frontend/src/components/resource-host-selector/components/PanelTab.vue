<template>
  <div class="resource-host-selector-panel-tab">
    <div
      class="tab-item"
      :class="{ active: modelValue === 'host' }"
      @click="handleChange('host')">
      {{ t('资源池主机') }}
    </div>
    <div class="tab-item"></div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<string>({
    default: 'host',
  });

  const handleChange = (value: string) => {
    modelValue.value = value;
  };
</script>
<style lang="less">
  .resource-host-selector-panel-tab {
    display: flex;
    font-size: 14px;
    font-weight: normal;
    background: #fafbfd;
    border-bottom: 1px solid #dcdee5;

    .tab-item {
      display: flex;
      height: 40px;
      color: #63656e;
      text-align: center;
      border-right: 1px solid #dcdee5;
      align-items: center;
      justify-content: center;
      flex: 1;

      &.active {
        position: relative;
        color: #313238;
        cursor: default;
        background: #fff;

        &::after {
          position: absolute;
          bottom: -2px;
          left: 0;
          width: 100%;
          height: 3px;
          background: #fff;
          content: '';
        }
      }
    }
  }
</style>
