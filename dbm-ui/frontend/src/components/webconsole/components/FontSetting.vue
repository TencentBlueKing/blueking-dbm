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
          :class="{ 'font-item-active': item.fontSize === modelValue.fontSize }"
          @click="() => handleChangeFontSize(item)">
          <DbIcon
            :style="item"
            type="aa" />
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface FontSetting {
    fontSize: string;
    lineHeight: string;
  }

  interface Emits {
    (e: 'change', value: FontSetting): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const modelValue = defineModel<FontSetting>({
    default: {
      fontSize: '12px',
      lineHeight: '20px',
    },
  });

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

  const handleChangeFontSize = (item: FontSetting) => {
    modelValue.value = item;
    emits('change', item);
  };
</script>
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
        align-items: end;
        justify-content: center;
      }

      .font-item-active {
        color: #dcdee5;
        background: #424242;
        border-radius: 1px;
      }
    }
  }
</style>
