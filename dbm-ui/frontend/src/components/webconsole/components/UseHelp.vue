<template>
  <div
    class="operate-item"
    :class="{ 'use-help-selected': showUseageHelp }"
    @click="handleToggleHelp">
    <div class="operate-item-inner">
      <DbIcon
        class="operate-icon"
        type="help-fill" />
      <span class="operate-title">{{ t('使用帮助') }}</span>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'toggleShowHelp'): void;
  }

  const emits = defineEmits<Emits>();

  const showUseageHelp = defineModel<boolean>('showUseageHelp', {
    default: false,
  });

  const { t } = useI18n();

  const handleToggleHelp = () => {
    emits('toggleShowHelp');
  };
</script>
