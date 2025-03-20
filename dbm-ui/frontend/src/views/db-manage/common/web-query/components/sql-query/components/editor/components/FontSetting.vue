<template>
  <BkPopover
    ext-cls="font-change-popover"
    placement="bottom"
    theme="dark">
    <div
      v-bk-tooltips="t('字号调整')"
      class="font-change-icon">
      <DbIcon type="aa" />
    </div>
    <template #content>
      <div class="font-change-main">
        <div
          v-for="(item, index) in fontSizeList"
          :key="index"
          class="font-item"
          :class="{ 'font-item-active': item === modelValue }"
          @click="() => handleChangeFontSize(item)">
          <DbIcon
            :style="{ fontSize: item + 'px' }"
            type="aa" />
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  type Emits = (e: 'change', value: number) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number>({
    default: 16,
  });

  const { t } = useI18n();

  const fontSizeList = [12, 14, 16];

  const handleChangeFontSize = (fontSize: number) => {
    modelValue.value = fontSize;
    emits('change', fontSize);
  };
</script>
<style lang="less" scoped>
  .font-change-icon {
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
  }
</style>
<style lang="less">
  .font-change-popover {
    padding: 0 !important;

    .font-change-main {
      display: flex;
      padding: 2px;
      cursor: pointer;
      background: #2e2e2e;
      border: 1px solid #3d3d3d;
      border-radius: 2px;
      box-shadow: 0 2px 6px 0 #0000001f;

      .font-item {
        display: flex;
        width: 28px;
        height: 28px;
        color: #979ba5;
        justify-content: center;
        align-items: center;
      }

      .font-item-active {
        color: #dcdee5;
        background: #424242;
        border-radius: 1px;
      }
    }
  }
</style>
