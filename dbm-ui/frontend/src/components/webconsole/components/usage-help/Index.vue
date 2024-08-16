<template>
  <div
    class="operate-item"
    :class="{ 'use-help-selected': modelValue }"
    @click="handleToggleHelp">
    <div class="operate-item-inner">
      <DbIcon
        class="operate-icon"
        type="help-fill" />
      <span class="operate-title">{{ t('使用帮助') }}</span>
    </div>
  </div>
  <div
    v-show="modelValue"
    class="using-help-wrap">
    <UsingHelpPanel
      :db-type="dbType"
      @hide="handleToggleHelp" />
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import UsingHelpPanel from './components/UsingHelpPanel.vue';

  interface Props {
    dbType?: DBTypes;
  }

  withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const modelValue = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();

  const handleToggleHelp = () => {
    modelValue.value = !modelValue.value;
  };
</script>
