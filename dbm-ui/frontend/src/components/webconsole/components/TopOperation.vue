<template>
  <div class="top-operate-main">
    <div
      class="operate-item"
      @click="handleClickClearScreen">
      <div class="operate-item-inner">
        <DbIcon
          class="operate-icon"
          type="clearing" />
        <span class="operate-title">{{ t('清屏') }}</span>
      </div>
    </div>
    <div class="operate-item">
      <div
        class="operate-item-inner"
        @click="handleClickExport">
        <DbIcon
          class="operate-icon"
          type="daochu" />
        <span class="operate-title">{{ t('导出') }}</span>
      </div>
    </div>
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
    <div class="operate-item-last">
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
      <div class="operate-icon">
        <div
          class="operate-icon-inner"
          @click="handleClickFullScreen">
          <DbIcon
            class="operate-icon"
            :type="isFullScreen ? 'un-full-screen' : 'full-screen'" />
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'clearCurrentScreen'): void;
    (e: 'toggleShowHelp'): void;
    (e: 'toggleFullScreen'): void;
    (
      e: 'fontSizeChange',
      value: {
        fontSize: string;
        lineHeight: string;
      },
    ): void;
    (e: 'export'): void;
  }

  const emits = defineEmits<Emits>();

  const showUseageHelp = defineModel<boolean>('showUseageHelp', {
    default: false,
  });

  const isFullScreen = defineModel<boolean>('isFullScreen', {
    default: false,
  });

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

  const handleClickClearScreen = () => {
    emits('clearCurrentScreen');
  };

  const handleToggleHelp = () => {
    emits('toggleShowHelp');
  };

  const handleChangeFontSize = (index: number) => {
    const currentFont = fontSizeList[index];
    currentFontSize.value = currentFont.fontSize;
    emits('fontSizeChange', currentFont);
  };

  const handleClickFullScreen = () => {
    isFullScreen.value = !isFullScreen.value;
    emits('toggleFullScreen');
  };

  const handleClickExport = () => {
    emits('export');
  };
</script>
<style lang="less">
  .top-operate-main {
    color: #c4c6cc;
    display: flex;
    min-width: 300px;

    .operate-item {
      position: relative;
      height: 40px;
      padding: 0 7px;
      display: flex;
      align-items: center;

      &::after {
        position: absolute;
        top: 12px;
        right: 0;
        width: 1px;
        height: 16px;
        background: #45464d;
        content: '';
      }

      .operate-item-inner {
        padding: 0 6px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;

        &:hover {
          background: #424242;
          border-radius: 2px;
        }

        .operate-icon {
          font-size: 16px;
        }

        .operate-title {
          margin-left: 5px;
        }
      }
    }

    .operate-item-last {
      height: 40px;
      display: flex;
      align-items: center;
      padding: 0 6px;
      cursor: pointer;
      // gap: 15px;

      .operate-icon {
        height: 40px;
        font-size: 16px;
        display: flex;
        align-items: center;

        .operate-icon-inner {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;

          &:hover {
            background: #424242;
            border-radius: 2px;
          }
        }
      }
    }

    .use-help-selected {
      background: #242424;
      color: #699df4;
    }
  }

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
