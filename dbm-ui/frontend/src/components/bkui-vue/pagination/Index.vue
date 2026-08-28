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
  <div class="dbm-pagination">
    <template
      v-for="(item, index) in visibleLayout"
      :key="item">
      <div
        v-if="item === 'total'"
        class="dbm-pagination-total"
        :class="getEdgeClass(index)">
        {{ t('共n条', { n: count }) }}
      </div>
      <div
        v-else-if="item === 'limit'"
        class="dbm-pagination-limit"
        :class="getEdgeClass(index)">
        <span>{{ t('每页') }}</span>
        <DbSelect
          class="dbm-pagination-limit-select"
          :clearable="false"
          :list="limitSelectList"
          :model-value="localLimit"
          size="small"
          :with-validate="false"
          @change="handleLimitChange" />
        <span>{{ t('条') }}</span>
        <slot name="limitAppend" />
      </div>
      <div
        v-else-if="item === 'list' && small"
        class="dbm-pagination-small-list"
        :class="getEdgeClass(index)">
        <div
          class="dbm-pagination-btn-pre"
          :class="{ 'is-disabled': isPrevDisabled }"
          @click="handlePrevPage">
          <AngleLeft />
        </div>
        <BkPopover
          v-model:is-show="isPickerShow"
          :arrow="false"
          boundary="body"
          ext-cls="dbm-pagination-picker-popover"
          placement="bottom"
          theme="light"
          trigger="click"
          :width="56">
          <div
            class="dbm-pagination-picker"
            :class="{ 'is-focused': isEditorFocused }">
            <span
              ref="editorRef"
              class="dbm-pagination-editor"
              contenteditable="true"
              spellcheck="false"
              @blur="handleEditorBlur"
              @focus="isEditorFocused = true"
              @keydown="handleEditorKeydown">
              {{ localCurrent }}
            </span>
            <span>/</span>
            <span class="dbm-pagination-small-list-total">{{ totalPageNum }}</span>
          </div>
          <template #content>
            <div class="dbm-pagination-picker-list">
              <div
                v-for="page in totalPageNum"
                :key="page"
                class="dbm-pagination-picker-item"
                :class="{ 'is-actived': page === localCurrent }"
                @click="handlePickerSelect(page)">
                {{ page }}
              </div>
            </div>
          </template>
        </BkPopover>
        <div
          class="dbm-pagination-btn-next"
          :class="{ 'is-disabled': isNextDisabled }"
          @click="handleNextPage">
          <AngleRight />
        </div>
      </div>
      <div
        v-else-if="item === 'list'"
        class="dbm-pagination-list"
        :class="getEdgeClass(index)">
        <div
          class="dbm-pagination-list-pre"
          :class="{ 'is-disabled': isPrevDisabled }"
          @click="handlePrevPage">
          <AngleLeft />
        </div>
        <div
          class="dbm-pagination-list-item"
          :class="{ 'is-active': localCurrent === 1 }"
          @click="handleItemClick(1)">
          1
        </div>
        <div
          v-if="showPrevBatch"
          class="dbm-pagination-list-pre-batch"
          @click="handlePrevBatch">
          <Ellipsis />
        </div>
        <div
          v-for="page in middleList"
          :key="page"
          class="dbm-pagination-list-item"
          :class="{ 'is-active': localCurrent === page }"
          @click="handleItemClick(page)">
          {{ page }}
        </div>
        <div
          v-if="showNextBatch"
          class="dbm-pagination-list-next-batch"
          @click="handleNextBatch">
          <Ellipsis />
        </div>
        <div
          v-if="totalPageNum > 1"
          class="dbm-pagination-list-item"
          :class="{ 'is-active': localCurrent === totalPageNum }"
          @click="handleItemClick(totalPageNum)">
          {{ totalPageNum }}
        </div>
        <div
          class="dbm-pagination-list-next"
          :class="{ 'is-disabled': isNextDisabled }"
          @click="handleNextPage">
          <AngleRight />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { AngleLeft, AngleRight, Ellipsis } from 'bkui-vue/lib/icon';
  import { range } from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    count: number;
    layout?: ('total' | 'list' | 'limit')[];
    limit?: number;
    limitList?: number[];
    modelValue?: number;
    showLimit?: boolean;
    showTotalCount?: boolean;
    small?: boolean;
  }

  type Emits = (e: 'change' | 'limitChange' | 'update:modelValue', value: number) => void;

  defineOptions({
    name: 'Pagination',
  });

  const props = withDefaults(defineProps<Props>(), {
    layout: () => ['total', 'list', 'limit'],
    limit: 10,
    limitList: () => [10, 20, 50, 100],
    modelValue: 1,
    showLimit: true,
    showTotalCount: true,
    small: false,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    limitAppend?: () => VNode;
  }>();

  // 页码区中间连续页码的个数
  const PAGE_ITEM_COUNT = 5;
  // 中间页码以当前页为中心，两侧各展示的个数
  const PAGE_ITEM_HALF = Math.floor(PAGE_ITEM_COUNT / 2);

  const { t } = useI18n();

  const editorRef = useTemplateRef<HTMLElement>('editorRef');

  const localCurrent = ref(props.modelValue);
  const localLimit = ref(props.limit);
  const isEditorFocused = ref(false);
  const isPickerShow = ref(false);

  const totalPageNum = computed(() => Math.max(1, Math.ceil(props.count / localLimit.value)));

  const isPrevDisabled = computed(() => localCurrent.value === 1);

  const isNextDisabled = computed(() => localCurrent.value === totalPageNum.value);

  const limitSelectList = computed(() => props.limitList.map((num) => ({ label: `${num}`, value: num })));

  // 首页与末页单独渲染，这里只算中间的连续页码：总页数不足时全部展开，超出后以当前页为中心滑动
  const middleList = computed(() => {
    if (totalPageNum.value <= 2) {
      return [];
    }
    if (totalPageNum.value <= PAGE_ITEM_COUNT + 2) {
      return range(2, totalPageNum.value);
    }
    const start = Math.min(totalPageNum.value - PAGE_ITEM_COUNT, Math.max(2, localCurrent.value - PAGE_ITEM_HALF));
    return range(start, start + PAGE_ITEM_COUNT);
  });

  const showPrevBatch = computed(
    () => totalPageNum.value > PAGE_ITEM_COUNT + 2 && localCurrent.value - PAGE_ITEM_HALF > 2,
  );

  const showNextBatch = computed(
    () => totalPageNum.value > PAGE_ITEM_COUNT + 2 && localCurrent.value + PAGE_ITEM_HALF < totalPageNum.value - 1,
  );

  // 首尾间距按实际渲染出来的块计算，被 showTotalCount / showLimit 关掉的块不占位
  const visibleLayout = computed(() =>
    props.layout.filter((item) => {
      if (item === 'total') {
        return props.showTotalCount;
      }
      if (item === 'limit') {
        return props.showLimit;
      }
      return true;
    }),
  );

  const getEdgeClass = (index: number) => ({
    'is-first': index === 0,
    'is-last': index === visibleLayout.value.length - 1,
  });

  const handleLimitChange = (limit: number) => {
    localLimit.value = limit;
    emits('limitChange', limit);
  };

  watch(
    () => props.modelValue,
    (modelValue) => {
      const page = Math.max(modelValue, 1);
      // count 未返回时总页数是兜底的 1，此时不能按它钳位，否则外部传入的初始页会被吞掉
      localCurrent.value = props.count > 0 ? Math.min(page, totalPageNum.value) : page;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.limit,
    (limit) => {
      localLimit.value = limit;
    },
  );

  // limitList 变化后当前每页条数可能已不在可选项中，回退到第一个可选项并通知外部
  watch(
    () => props.limitList,
    (limitList) => {
      if (limitList.length > 0 && !limitList.includes(localLimit.value)) {
        handleLimitChange(limitList[0]);
      }
    },
    {
      immediate: true,
    },
  );

  // 切换每页条数导致总页数变小时，修正超出范围的当前页
  watch(totalPageNum, (total) => {
    if (localCurrent.value > total) {
      localCurrent.value = total;
    }
  });

  watch(localCurrent, (current) => {
    emits('update:modelValue', current);
    emits('change', current);
  });

  const handlePrevPage = () => {
    if (!isPrevDisabled.value) {
      localCurrent.value = localCurrent.value - 1;
    }
  };

  const handleNextPage = () => {
    if (!isNextDisabled.value) {
      localCurrent.value = localCurrent.value + 1;
    }
  };

  const handleItemClick = (page: number) => {
    localCurrent.value = page;
  };

  const handlePrevBatch = () => {
    localCurrent.value = Math.max(1, localCurrent.value - PAGE_ITEM_COUNT);
  };

  const handleNextBatch = () => {
    localCurrent.value = Math.min(totalPageNum.value, localCurrent.value + PAGE_ITEM_COUNT);
  };

  const handlePickerSelect = (page: number) => {
    localCurrent.value = page;
    isPickerShow.value = false;
  };

  // 不在这里关 popover：点页码选项时 mousedown 先触发本次 blur，提前关掉会让后续 click 落不到选项上
  const handleEditorBlur = () => {
    isEditorFocused.value = false;
    const editorEl = editorRef.value!;
    const page = Number(editorEl.textContent);
    if (Number.isInteger(page) && page >= 1 && page <= totalPageNum.value) {
      localCurrent.value = page;
    }
    // 输入非法时 localCurrent 未变化，模板不会重新渲染，需手动把内容还原为当前页
    editorEl.textContent = `${localCurrent.value}`;
  };

  const handleEditorKeydown = (event: KeyboardEvent) => {
    if (['Enter', 'NumpadEnter'].includes(event.code)) {
      // 阻止回车在可编辑区域插入换行，改为直接失焦提交
      event.preventDefault();
      isPickerShow.value = false;
      editorRef.value!.blur();
    }
  };
</script>

<style lang="less">
  .dbm-pagination {
    display: flex;
    width: 100%;
    font-size: 12px;
    letter-spacing: normal;
    color: #63656e;
    user-select: none;
    align-items: center;

    > * {
      margin: 0 6px;
    }

    > .is-first {
      margin-left: 0;
    }

    // 调用方给了宽度（如占满一行）时，最后一块吃掉剩余空间靠右，其余块靠左
    > .is-last {
      margin-right: 0;
      margin-left: auto;
    }
  }

  .dbm-pagination-total {
    display: flex;
  }

  .dbm-pagination-limit {
    display: flex;
    align-items: center;

    .dbm-pagination-limit-select {
      width: 60px;
      margin: 0 4px;

      .dbm-select-input-box {
        background-color: #f0f1f5;
        border-color: #f0f1f5;
      }

      &:hover .dbm-select-input-box {
        background-color: #eaebf0;
        border-color: #eaebf0;
      }

      &.is-focus .dbm-select-input-box {
        background-color: #fff;
        border-color: #3a84ff;
      }
    }
  }

  .dbm-pagination-list {
    display: flex;
    margin-right: 8px;
    align-items: center;

    .dbm-pagination-list-pre,
    .dbm-pagination-list-next,
    .dbm-pagination-list-pre-batch,
    .dbm-pagination-list-next-batch,
    .dbm-pagination-list-item {
      display: flex;
      height: 32px;
      min-width: 32px;
      padding: 0 4px;
      margin: 0 2px;
      color: #63656e;
      cursor: pointer;
      background: #fff;
      border-radius: 2px;
      align-items: center;
      justify-content: center;

      &:hover {
        background: #f0f1f5;
      }

      &.is-active {
        color: #3a84ff;
        background: #e1ecff;
      }
    }

    .dbm-pagination-list-pre,
    .dbm-pagination-list-next {
      font-size: 20px;
      color: #979ba5;

      &.is-disabled {
        color: #dcdee5;
        cursor: not-allowed;
        background-color: transparent;
      }
    }
  }

  .dbm-pagination-small-list {
    display: flex;
    align-items: center;

    .dbm-pagination-btn-pre,
    .dbm-pagination-btn-next {
      display: flex;
      width: 26px;
      height: 26px;
      font-size: 20px;
      color: #979ba5;
      cursor: pointer;
      align-items: center;
      justify-content: center;

      &:hover {
        color: #3a84ff;
        background: #f0f1f5;
      }

      &.is-disabled {
        color: #dcdee5;
        cursor: not-allowed;
        background: transparent;
      }
    }

    .dbm-pagination-picker {
      display: flex;
      height: 26px;
      margin: 0 4px;
      cursor: pointer;
      background-color: #f0f1f5;
      border: 1px solid #f0f1f5;
      border-radius: 2px;
      align-items: center;

      &:hover {
        background-color: #eaebf0;
        border-color: #eaebf0;
      }

      &.is-focused {
        background-color: #fff;
        border-color: #3a84ff;
        box-shadow: 0 0 4px #3a84ff66;
      }
    }

    .dbm-pagination-editor {
      height: 16px;
      min-width: 23px;
      padding: 0 4px 0 8px;
      line-height: 16px;
      text-align: center;
      background-color: transparent;
      border: 0;
      outline: none;
    }

    .dbm-pagination-small-list-total {
      padding: 0 8px 0 4px;
    }
  }

  // popover 内容区自带 12px 内边距，页码选项要通栏展示，按 bk 的类名叠加权重覆盖
  .bk-popover.bk-pop2-content.dbm-pagination-picker-popover {
    padding: 0;

    .dbm-pagination-picker-list {
      max-height: 216px;
      padding: 4px 0;
      overflow: auto;

      .dbm-pagination-picker-item {
        height: 32px;
        padding: 0 10px;
        font-size: 12px;
        line-height: 32px;
        color: #63656e;
        cursor: pointer;

        &:hover,
        &.is-actived {
          color: #3a84ff;
          background: #f4f6fa;
        }
      }
    }
  }
</style>
