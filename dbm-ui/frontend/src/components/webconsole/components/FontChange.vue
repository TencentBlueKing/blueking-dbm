<template>
  <BkPopover
    ext-cls="font-change-popover"
    placement="bottom"
    theme="dark">
    <div
      v-bk-tooltips="t('字号调整')"
      class="operate-icon">
      <div class="operate-icon-inner">
        <DbIcon type="aa" />
      </div>
    </div>
    <template #content>
      <div class="font-change-main">
        <div
          v-for="(item, index) in fontSizeList"
          :key="index"
          class="font-item"
          :class="{ 'font-item-active': item.fontSize === currentFontSize }"
          @click="() => handleChangeFontSize(index)">
          <DbIcon
            :style="{ 'font-size': item }"
            type="aa" />
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (
      e: 'fontSizeChange',
      value: {
        fontSize: string;
        lineHeight: string;
      },
    ): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const currentFontSize = ref('12px');

  const fontSizeList = [
    {
      fontSize: '12px',
      lineHeight: '20px',
    },
    {
      fontSize: '14px',
      lineHeight: '22px',
    },
    {
      fontSize: '16px',
      lineHeight: '24px',
    },
  ];

  const handleChangeFontSize = (index: number) => {
    const currentFont = fontSizeList[index];
    currentFontSize.value = currentFont.fontSize;
    emits('fontSizeChange', currentFont);
  };
</script>
<style lang="less">
  .font-change-popover {
    padding: 0 !important;

    .font-change-main {
      display: flex;
      padding: 2px;
      background: #2e2e2e;
      border: 1px solid #3d3d3d;
      box-shadow: 0 2px 6px 0 #0000001f;
      border-radius: 2px;
      cursor: pointer;

      .font-item {
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #979ba5;
      }

      .font-item-active {
        background: #424242;
        border-radius: 1px;
        color: #dcdee5;
      }
    }
  }
</style>
