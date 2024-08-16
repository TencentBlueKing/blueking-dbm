<template>
  <div class="operate-item">
    <div class="operate-item-switcher">
      <BkSwitcher
        v-model="modelValue"
        v-bk-tooltips="{
          content: t('开启后可正常显示中文'),
          disabled: modelValue,
        }"
        theme="primary"
        @change="handleRawSwitch" />
      <span class="operate-title ml-5">{{ t('Raw 模式') }}</span>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  interface Props {
    dbType: DBTypes;
  }

  interface Emits {
    (e: 'change', value?: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const modelValue = defineModel<boolean>({
    default: false,
  });

  const handleRawSwitch = (value: boolean) => {
    modelValue.value = value;
    emits('change', props.dbType === DBTypes.REDIS ? value : undefined);
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
