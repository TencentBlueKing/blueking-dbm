<template>
  <div
    v-clickoutside="handleClickToolsOutside"
    class="canvas-tools-main">
    <div class="operations-main">
      <div
        class="tool-item"
        :class="{ 'tool-item-active': toolActiveMap.map }"
        @click="() => handleClickTool('map')">
        <DbIcon
          v-bk-tooltips="'Map'"
          type="map" />
      </div>
      <div class="split-line"></div>
      <div class="zoom-main">
        <div class="tool-item">
          <DbIcon
            v-bk-tooltips="t('缩小')"
            class="zoom-icon"
            type="1-jianhaobeifen-2"
            @click="handleZoomOut" />
        </div>
        <div class="zoom-display">{{ zoomValue }}%</div>
        <div class="tool-item">
          <DbIcon
            v-bk-tooltips="t('放大')"
            class="zoom-icon"
            type="1-jianhaobeifen"
            @click="handleZoomIn" />
        </div>
      </div>
      <div class="split-line"></div>
      <div class="tool-item">
        <DbIcon
          v-bk-tooltips="t('复位')"
          type="dingwei"
          @click="handleReset" />
      </div>
      <div class="split-line"></div>
      <div
        class="tool-item"
        :class="{ 'tool-item-active': toolActiveMap.legend }"
        @click="() => handleClickTool('legend')">
        <DbIcon
          v-bk-tooltips="t('图例')"
          type="legend" />
      </div>
      <div class="split-line"></div>
      <div
        class="tool-item"
        :class="{ 'tool-item-active': toolActiveMap.keyboard }"
        @click="() => handleClickTool('keyboard')">
        <DbIcon
          v-bk-tooltips="t('快捷键')"
          type="keyboard" />
      </div>
      <div class="split-line"></div>
      <div
        class="tool-item"
        @click="handleToggleFullScreen">
        <DbIcon
          v-bk-tooltips="screenInfo.tip"
          :type="screenInfo.icon" />
      </div>
    </div>
    <div
      v-show="toolActiveMap.legend"
      class="legend-container-main">
      <div class="title">
        {{ t('图例说明') }}
      </div>
      <div class="list-main">
        <div class="icon-list">
          <div
            v-for="item in iconList"
            :key="item.type"
            class="icon-item">
            <DbIcon :type="item.type" />
            <div class="name">{{ item.name }}</div>
          </div>
        </div>
        <div class="status-list">
          <div
            v-for="(item, index) in statusList"
            :key="index"
            class="status-item">
            <div
              class="sign"
              :style="{ backgroundColor: item.color }"></div>
            <div class="name">{{ item.name }}</div>
          </div>
        </div>
      </div>
    </div>
    <div
      v-show="toolActiveMap.keyboard"
      class="hot-key-main">
      <div class="hot-key-title">
        {{ t('快捷键') }}
      </div>
      <div class="hot-key-list">
        <div
          v-for="(item, index) in hotKeyList"
          :key="index"
          class="hot-key-item">
          <span class="hot-key-text">{{ item.name }}</span>
          <span class="hot-key-code">{{ item.action }}</span>
          <span class="hot-key-code">{{ item.code }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'toggleFullScreen'): void;
    (e: 'zoomChange', value: number): void;
    (e: 'reset'): void;
  }

  interface Exposes {
    showMiniMap: () => void;
    zoomIn: () => void;
    zoomOut: () => void;
    zoomReset: () => void;
  }

  const emits = defineEmits<Emits>();

  const zoomValue = defineModel<number>('zoom', {
    default: 100,
  });

  const { t } = useI18n();

  const isFullScreen = ref(false);

  const toolActiveMap = reactive<Record<string, boolean>>({
    keyboard: false,
    legend: false,
    map: false,
  });

  const screenInfo = computed(() => ({
    icon: isFullScreen.value ? 'un-full-screen' : 'full-screen',
    tip: isFullScreen.value ? t('取消全屏') : t('全屏'),
  }));

  const hotKeyList = [
    {
      action: 'Ctrl',
      code: t('滚轮'),
      name: t('缩放'),
    },
    {
      action: 'Ctrl',
      code: '+',
      name: t('放大'),
    },
    {
      action: 'Ctrl',
      code: '-',
      name: t('缩小'),
    },
    {
      action: 'Ctrl',
      code: '0',
      name: t('还原'),
    },
  ];

  const iconList = [
    {
      name: t('并行网关'),
      type: 'parallel-gateway',
    },
    {
      name: t('汇聚网关'),
      type: 'converge-gateway',
    },
    {
      name: t('条件网关'),
      type: 'branch-gateway',
    },
    {
      name: t('开始节点'),
      type: 'kaishi',
    },
    {
      name: t('结束节点'),
      type: 'jieshu',
    },
  ];

  const statusList = [
    {
      color: '#C4C6CC',
      name: t('待执行'),
    },
    {
      color: '#3A84FF',
      name: t('执行中'),
    },
    {
      color: '#2CAF5E',
      name: t('执行成功'),
    },
    {
      color: '#F59500',
      name: t('待继续'),
    },
    {
      color: '#EA3636',
      name: t('执行失败'),
    },
    {
      color: '#8EBF76',
      name: t('已跳过'),
    },
  ];

  const G6_MINIMAP_CLASS_NAME = 'g6-minimap';
  const G6_MINIMAP_SHOW_CLASS_NAME = 'g6-minimap-show';

  watch(zoomValue, () => {
    emits('zoomChange', zoomValue.value);
  });

  const zoomOut = () => {
    if (zoomValue.value <= 25) {
      return;
    }

    zoomValue.value -= 25;
  };

  const zoomIn = () => {
    if (zoomValue.value >= 150) {
      return;
    }
    zoomValue.value += 25;
  };

  const zoomReset = () => {
    zoomValue.value = 100;
  };

  const handleZoomOut = () => {
    initToolsDisplay();
    zoomOut();
  };

  const handleZoomIn = () => {
    initToolsDisplay();
    zoomIn();
  };

  const handleReset = () => {
    initToolsDisplay();
    zoomReset();
    emits('reset');
  };

  const handleToggleFullScreen = () => {
    isFullScreen.value = !isFullScreen.value;
    emits('toggleFullScreen');
  };

  const showMiniMap = () => {
    const minimapDom = document.getElementsByClassName(G6_MINIMAP_CLASS_NAME)[0];
    minimapDom.classList.add(G6_MINIMAP_SHOW_CLASS_NAME);
  };

  const handleClickTool = (type: string) => {
    Object.keys(toolActiveMap).forEach((key) => {
      if (key === type) {
        return;
      }
      toolActiveMap[key] = false;
    });
    toolActiveMap[type] = !toolActiveMap[type];
    if (type === 'map') {
      if (toolActiveMap.map) {
        showMiniMap();
      } else {
        hideMiniMap();
      }
    } else {
      hideMiniMap();
    }
  };

  const hideMiniMap = () => {
    const minimapDom = document.getElementsByClassName(G6_MINIMAP_CLASS_NAME)[0];
    minimapDom.classList.remove(G6_MINIMAP_SHOW_CLASS_NAME);
  };

  const handleClickToolsOutside = (e: any) => {
    if (!e.target.parentNode.classList.contains(G6_MINIMAP_SHOW_CLASS_NAME)) {
      Object.keys(toolActiveMap).forEach((key) => {
        toolActiveMap[key] = false;
      });
      hideMiniMap();
    }
  };

  const initToolsDisplay = () => {
    Object.keys(toolActiveMap).forEach((key) => {
      toolActiveMap[key] = false;
    });
    hideMiniMap();
  };

  defineExpose<Exposes>({
    showMiniMap: () => {
      if (toolActiveMap.map) {
        showMiniMap();
      }
    },
    zoomIn,
    zoomOut,
    zoomReset,
  });
</script>
<style lang="less">
  .canvas-tools-main {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 300px;

    .operations-main {
      display: flex;
      width: 100%;
      height: 36px;
      padding: 0 10px;
      margin-bottom: 4px;
      font-size: 14px;
      color: #9b9da1;
      cursor: pointer;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 #0000001a;
      align-items: center;

      .tool-item {
        display: flex;
        width: 28px;
        height: 28px;
        color: #979ba5;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        &:hover {
          color: #3a84ff;
          background-color: #e1ecff;
        }

        &.tool-item-active {
          color: #3a84ff;
          background-color: #e1ecff;
        }
      }

      .split-line {
        width: 1px;
        height: 15px;
        margin: 0 6px;
        background-color: #dcdee5;
      }

      .zoom-main {
        display: flex;
        width: 86px;
        align-items: center;
        justify-content: center;

        .zoom-icon {
          font-size: 16px;

          &:hover {
            color: #3a84ff;
          }
        }

        .zoom-display {
          margin: 0 6px;
          font-size: 10px;
          color: #979ba5;
        }
      }
    }

    .legend-container-main {
      width: 100%;
      height: 216px;
      padding: 8px 12px;
      background: #fff;
      border-radius: 4px;
      box-shadow: 0 1px 6px 0 #0000001f;

      .title {
        margin-bottom: 12px;
        font-size: 14px;
        color: #313238;
      }

      .list-main {
        display: flex;

        .icon-list {
          display: flex;
          flex-direction: column;
          gap: 13px;
          margin-right: 86px;

          .icon-item {
            display: flex;
            height: 16px;
            font-size: 14px;
            color: #979ba5;
            align-items: center;
            gap: 13px;

            .name {
              font-size: 12px;
              color: #4d4f56;
            }
          }
        }

        .status-list {
          display: flex;
          flex-direction: column;
          gap: 13px;

          .status-item {
            display: flex;
            align-items: center;
            gap: 16px;
            height: 16px;

            .sign {
              width: 9px;
              height: 9px;
            }

            .name {
              font-size: 12px;
              color: #4d4f56;
            }
          }
        }
      }
    }

    .hot-key-main {
      width: 100%;
      padding: 8px 12px;
      background: #fff;
      border-radius: 4px;
      box-shadow: 0 1px 6px 0 #0000001f;

      .hot-key-title {
        padding-bottom: 8px;
        color: #313238;
      }

      .hot-key-item {
        display: flex;
        padding: 8px 0 6px;
        font-size: 12px;
        color: #63656e;
        align-items: center;
      }

      .hot-key-text {
        margin-right: 32px;
      }

      .hot-key-code {
        min-width: 20px;
        padding: 0 6px;
        margin-right: 8px;
        line-height: 18px;
        border: 1px solid #dcdee5;
        border-radius: 2px;
      }
    }
  }

  .g6-minimap {
    top: 56px !important;
    right: 16px !important;
    left: auto !important;
    display: none !important;
    border: none !important;
    border-radius: 4px;
    box-shadow: 0 1px 6px 0 #0000001f;
  }

  .g6-minimap-show {
    display: block !important;
  }
</style>
