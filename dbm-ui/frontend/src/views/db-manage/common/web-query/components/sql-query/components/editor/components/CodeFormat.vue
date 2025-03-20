<template>
  <div
    v-bk-tooltips="toolTips"
    class="code-format-icon"
    :class="{ 'code-format-icon-disabled': isDisabled }"
    @click="handleClickFormat">
    <DbIcon type="code-2" />
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Props {
    data?: string;
  }

  type Emits = (e: 'format') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isDisabled = computed(() => !props.data);
  const toolTips = computed(() => (isDisabled.value ? t('暂无内容，无法格式化') : t('格式化')));

  const handleClickFormat = () => {
    if (isDisabled.value) {
      return;
    }

    emits('format');
  };
</script>
<style lang="less" scoped>
  .code-format-icon {
    display: flex;
    width: 28px;
    height: 28px;
    color: #c4c6cc;
    border-radius: 2px;
    justify-content: center;
    align-items: center;

    &:hover {
      background: #424242;
    }

    &.code-format-icon-disabled {
      color: #63656e;
      cursor: not-allowed !important;
    }
  }
</style>
