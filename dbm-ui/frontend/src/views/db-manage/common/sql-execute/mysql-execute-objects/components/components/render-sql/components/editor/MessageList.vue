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
    v-if="data.length > 0"
    class="sql-error-message-list"
    :class="[statusClass, { collapsed }]">
    <!-- 可点击展开/收起的汇总栏 -->
    <div
      class="check-summary"
      @click="handleToggleCollapse">
      <div class="summary-text">
        <span class="summary-label">{{ t('检查结果') }}：</span>
        <template v-if="totalMap.errorNum > 0">
          <span class="summary-count-error">{{ totalMap.errorNum }} {{ t('个错误') }}</span>
        </template>
        <template v-if="totalMap.warningNum > 0">
          <span
            v-if="totalMap.errorNum > 0"
            class="summary-divider">
            ·
          </span>
          <span class="summary-count-warn">{{ totalMap.warningNum }} {{ t('个风险提示') }}</span>
        </template>
      </div>
      <div
        class="summary-toggle"
        :class="{ 'is-collapsed': collapsed }">
        <span>{{ collapsed ? t('展开') : t('收起') }}</span>
        <DbIcon
          class="toggle-arrow"
          type="bk-dbm-icon db-icon-down-shape" />
      </div>
    </div>

    <!-- 列表区域：随内容撑开，>5 条时限高内滚动 -->
    <div
      class="check-list-wrapper"
      :style="listWrapperStyle">
      <div
        v-for="(item, index) in data"
        :key="index"
        class="item-row"
        :class="{ 'is-active': activeLine === item.line }"
        @click="handleItemClick(item.line)">
        <DbIcon
          v-if="item.type === 'error'"
          class="item-icon"
          type="bk-dbm-icon db-icon-close-circle-shape" />
        <DbIcon
          v-else
          class="item-icon item-icon--warning"
          type="bk-dbm-icon db-icon-early-warning" />
        <span
          class="item-tag"
          :class="`tag-${item.category}`">
          {{ CATEGORY_MAP[item.category] || '' }}
        </span>
        <span
          :ref="(el: any) => setMessageRef(el, index)"
          v-bk-tooltips="{
            disabled: !isOverflowMap[index],
            content: item.message,
          }"
          class="item-message"
          @mouseenter="handleMessageEnter(index)">
          {{ item.message }}
        </span>
        <span class="item-line">[{{ t('行') }} {{ item.line }}]</span>
      </div>
    </div>
  </div>
  <div
    v-else
    class="sql-error-message-list success-message">
    <div class="success-summary">
      <span class="summary-label">{{ t('检查结果') }}：</span>
      <span class="summary-success-text">{{ t('检测通过') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  export type IMessageList = Array<{
    category: string;
    line: number;
    message: string;
    type: 'warning' | 'error';
  }>;

  interface Props {
    data?: IMessageList;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 记录每一行 message 是否溢出
  const isOverflowMap = ref<Record<number, boolean>>({});

  // 鼠标进入时检测是否溢出，仅溢出时才启用 tooltip
  const handleMessageEnter = (index: number) => {
    const el = messageRefMap.get(index);
    if (!el) return;
    isOverflowMap.value = {
      ...isOverflowMap.value,
      [index]: el.offsetWidth < el.scrollWidth,
    };
  };

  // 缓存每个 message span 的 DOM 引用
  const messageRefMap = new Map<number, HTMLElement>();

  const setMessageRef = (el: any, index: number) => {
    if (el) {
      messageRefMap.set(index, el.$el ?? el);
    } else {
      messageRefMap.delete(index);
    }
  };

  type Emits = (e: 'goto-line', line: number) => void;

  const activeLine = ref<number>(-1);
  const collapsed = ref(false);

  const CATEGORY_MAP = computed<Record<string, string>>(() => ({
    ban_command: t('禁用命令'),
    high_risk: t('高危变更'),
    syntax_error: t('语法错误'),
  }));

  const totalMap = computed(() => {
    let errorNum = 0;
    let warningNum = 0;
    props.data.forEach((item) => {
      if (item.type === 'error') {
        errorNum += 1;
      } else if (item.type === 'warning') {
        warningNum += 1;
      }
    });
    return { errorNum, warningNum };
  });

  const statusClass = computed(() => {
    if (totalMap.value.errorNum > 0) return 'is-error';
    if (totalMap.value.warningNum > 0) return 'is-warning';
    return '';
  });

  // 条目超过 5 条时限制高度，否则随内容撑开
  const listWrapperStyle = computed(() => {
    if (collapsed.value) return { display: 'none' };
    return props.data.length > 5 ? { maxHeight: '220px' } : {};
  });

  const handleToggleCollapse = () => {
    collapsed.value = !collapsed.value;
  };

  const handleItemClick = (line: number) => {
    activeLine.value = line;
    emits('goto-line', line);
  };
</script>

<style lang="less">
  .sql-error-message-list {
    display: flex;
    flex-direction: column;
    font-size: 12px;
    background: #252526;
    border-top: 4px solid #ea3636;

    &.is-warning {
      border-top-color: #ff9c01;
    }

    // 收起时列表区域折叠为 0，容器高度自动收缩
    &.collapsed .check-list-wrapper {
      display: none;
    }

    &.success-message {
      display: flex;
      height: 48px;
      padding: 10px 16px;
    }

    .success-summary {
      display: flex;
      gap: 4px;
      line-height: 28px;
    }

    .summary-success-text {
      color: #3fc06d;
      font-weight: 600;
    }

    /* ===== 汇总栏（可点击展开/收起，固定高度不随列表变化）===== */
    .check-summary {
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
      padding: 10px 16px;
      cursor: pointer;
      user-select: none;
      transition: background-color 0.15s;

      &:hover {
        background: rgb(255 255 255 / 6%);
      }
    }

    .summary-text {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #cccccc;
    }

    .summary-label {
      color: #9d9d9d;
      flex-shrink: 0;
    }

    .summary-count-error {
      margin-left: 2px;
      color: #ff6b6b;
      font-weight: 600;
    }

    .summary-count-warn {
      margin-left: 2px;
      color: #ffb648;
      font-weight: 600;
    }

    .summary-divider {
      margin: 0 4px;
      color: #6a6a6a;
    }

    .summary-toggle {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #9d9d9d;
      font-size: 12px;
      flex-shrink: 0;
    }

    .toggle-arrow {
      font-size: 12px;
      transition: transform 0.2s ease;
      color: #9d9d9d;
    }

    .is-collapsed .toggle-arrow {
      transform: rotate(-90deg);
    }

    /* ===== 列表区域：flex 填充，>5 条限高内滚动 ===== */
    .check-list-wrapper {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      border-top: 1px solid #2d2d2d;
      padding: 6px 0;

      // >5 条时限制最大高度
      &.has-limit {
        max-height: 220px;
      }

      // 自定义滚动条（与原型一致）
      &::-webkit-scrollbar {
        width: 4px;
      }

      &::-webkit-scrollbar-track {
        background: transparent;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255 / 16%);
        border-radius: 2px;

        &:hover {
          background: rgba(255, 255, 255 / 24%);
        }
      }

      .item-row {
        display: flex;
        align-items: center;
        padding: 6px 12px;
        line-height: 20px;
        cursor: pointer;
        border-left: 2px solid transparent;
        transition:
          background 0.15s ease,
          border-color 0.15s ease;

        &:hover {
          background: #2a2d2e;
          border-left-color: #3a84ff;

          .item-line {
            color: #cccccc;
          }

          .item-message {
            color: #ffffff;
          }
        }

        &:active {
          background: #323436;
        }

        &.is-active {
          background: rgb(58 132 255 / 10%);
          border-left-color: #3a84ff;
        }

        // 图标 — 形状 + 颜色双编码
        .item-icon {
          flex-shrink: 0;
          width: 14px;
          height: 14px;
          margin-right: 10px;
          font-size: 14px;
          color: #ea3636;

          &--warning {
            color: #ff9c01;
          }
        }

        // 分类标签 — 中性灰色
        .item-tag {
          flex-shrink: 0;
          margin-right: 8px;
          padding: 1px 6px;
          font-size: 11px;
          line-height: 18px;
          white-space: nowrap;
          color: #9d9d9d;
          background: rgba(255, 255, 255 / 8%);
          border-radius: 2px;
        }

        // 详情文本
        .item-message {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: #d4d4d4;
        }

        // 行号
        .item-line {
          flex-shrink: 0;
          margin-left: 6px;
          color: #6a6a6a;
          font-size: 11.5px;
        }
      }
    }
  }
</style>
