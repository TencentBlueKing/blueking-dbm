<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    v-clickoutside="handleClickToolsOutside"
    class="canvas-tools-main">
    <div class="operations-main">
      <div
        class="tool-item"
        :class="{ 'tool-item-active': activeTool === 'map' }"
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
        <div
          class="zoom-display"
          :class="{ 'zoom-display-active': activeTool === 'zoom' }"
          @click="() => handleClickTool('zoom')">
          {{ zoom }}%
        </div>
        <div class="tool-item">
          <DbIcon
            v-bk-tooltips="t('放大')"
            class="zoom-icon"
            type="1-jianhaobeifen"
            @click="handleZoomIn" />
        </div>
        <div
          v-show="activeTool === 'zoom'"
          class="zoom-options-main">
          <div
            v-for="item in ZOOM_OPTIONS"
            :key="item"
            class="zoom-option-item"
            @click="() => handleSelectZoom(item)">
            {{ item }}%
          </div>
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
        :class="{ 'tool-item-active': activeTool === 'legend' }"
        @click="() => handleClickTool('legend')">
        <DbIcon
          v-bk-tooltips="t('图例')"
          type="legend" />
      </div>
      <div class="split-line"></div>
      <div
        class="tool-item"
        :class="{ 'tool-item-active': activeTool === 'keyboard' }"
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
      v-show="activeTool === 'legend'"
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
      v-show="activeTool === 'keyboard'"
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { NODE_STATUS_META } from '@views/task-history/detail/utils';

  import { ZOOM_OPTIONS } from '../utils';

  interface Props {
    isFullScreen: boolean;
    zoom: number;
  }

  interface Emits {
    (e: 'toggleFullScreen'): void;
    (e: 'zoomChange', value: number): void;
    (e: 'reset'): void;
  }

  type ToolType = '' | 'keyboard' | 'legend' | 'map' | 'zoom';

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  // 缩略图是 G6 插件挂在画布容器里的 DOM，显隐由容器上的类名控制，这里只上报开关状态
  const isMinimapVisible = defineModel<boolean>('minimapVisible', {
    default: false,
  });

  const { t } = useI18n();

  // 四个面板互斥，同时只会亮一个
  const activeTool = ref<ToolType>('');

  // 全屏状态以父组件的 useFullscreen 为准，自己记录的话按 Esc 退出全屏时会和实际状态脱节
  const screenInfo = computed(() => ({
    icon: props.isFullScreen ? 'un-full-screen' : 'full-screen',
    tip: props.isFullScreen ? t('取消全屏') : t('全屏'),
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
      name: t('复位'),
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

  const statusList = (['CREATED', 'RUNNING', 'FINISHED', 'TODO', 'FAILED', 'SKIPPED'] as const).map((status) => ({
    color: NODE_STATUS_META[status].color,
    name: NODE_STATUS_META[status].text,
  }));

  watch(activeTool, () => {
    isMinimapVisible.value = activeTool.value === 'map';
  });

  // ± 按钮在快捷档位之间跳。Ctrl + 滚轮与快捷键是 1% 连续缩放，当前值可能停在档位之外（如 137%），
  // 所以按大小关系取相邻档位而不是按下标取；已经在首尾档位时 find 取不到值，保持不动
  const handleZoomOut = () => {
    activeTool.value = '';
    const target = _.findLast(ZOOM_OPTIONS, (item) => item < props.zoom);
    if (target) {
      emits('zoomChange', target);
    }
  };

  const handleZoomIn = () => {
    activeTool.value = '';
    const target = ZOOM_OPTIONS.find((item) => item > props.zoom);
    if (target) {
      emits('zoomChange', target);
    }
  };

  const handleSelectZoom = (value: number) => {
    activeTool.value = '';
    emits('zoomChange', value);
  };

  const handleReset = () => {
    activeTool.value = '';
    emits('reset');
  };

  const handleToggleFullScreen = () => {
    emits('toggleFullScreen');
  };

  const handleClickTool = (type: ToolType) => {
    activeTool.value = activeTool.value === type ? '' : type;
  };

  const handleClickToolsOutside = (e: MouseEvent) => {
    // 缩略图画在工具栏外面，点它不算点到外面，否则一点缩略图整排面板就收了
    if ((e.target as Element | null)?.closest?.('.g6-minimap')) {
      return;
    }
    activeTool.value = '';
  };
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
        position: relative;
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

          &:hover {
            color: #3a84ff;
          }

          &.zoom-display-active {
            color: #3a84ff;
          }
        }

        // 画在工具栏内部而不是用 popover：全屏时全屏元素是画布容器，teleport 到 body 的浮层看不见
        .zoom-options-main {
          position: absolute;
          top: calc(100% + 8px);
          left: 50%;
          width: 76px;
          padding: 4px 0;
          background: #fff;
          border-radius: 4px;
          transform: translateX(-50%);
          box-shadow: 0 1px 6px 0 #0000001f;

          .zoom-option-item {
            padding: 0 12px;
            font-size: 12px;
            line-height: 32px;
            color: #63656e;

            &:hover {
              color: #3a84ff;
              background-color: #e1ecff;
            }
          }
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
              border-radius: 50%;
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
</style>
