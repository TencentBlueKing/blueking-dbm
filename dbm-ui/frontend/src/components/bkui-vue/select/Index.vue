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
    ref="rootRef"
    class="dbm-select"
    :class="{
      'is-disabled': disabled,
      'is-focus': isFocus,
      'is-huge': size === 'huge',
      'is-large': size === 'large',
      'is-popover-show': isPopoverShow,
      'is-simplicity': behavior === 'simplicity',
      'is-small': size === 'small',
    }">
    <div
      ref="triggerRef"
      class="dbm-select-trigger"
      :style="triggerStyle"
      @click="handleTogglePopover"
      @mouseenter="isHover = true"
      @mouseleave="isHover = false">
      <slot
        v-if="$slots.trigger"
        name="trigger"
        :selected="selectedTags" />
      <template v-else>
        <TagTrigger
          v-if="multipleMode === 'tag'"
          ref="tagTriggerRef"
          v-model="customOptionName"
          :behavior="behavior"
          :collapse-tags="isCollapseTags"
          :disabled="disabled"
          :filterable="isInput"
          :placeholder="localPlaceholder"
          :selected="selectedTags"
          :tag-theme="tagTheme"
          @enter="handleCreateCustomOption"
          @remove="handleDeleteTag">
          <template
            v-if="$slots.tag"
            #default="{ selected: selectedList }">
            <slot
              name="tag"
              :selected="selectedList" />
          </template>
          <template
            v-if="hasPrefix"
            #prefix>
            <div class="dbm-select-prefix-area">
              <slot name="prefix">
                <span>{{ prefix }}</span>
              </slot>
            </div>
          </template>
          <template
            v-if="$slots.tagRender"
            #tagRender="tagItem">
            <slot
              name="tagRender"
              v-bind="tagItem" />
          </template>
        </TagTrigger>
        <div
          v-else
          class="dbm-select-input-box"
          :class="{ 'has-prefix': hasPrefix }">
          <div
            v-if="hasPrefix"
            class="dbm-select-prefix-area">
            <slot name="prefix">
              <span>{{ prefix }}</span>
            </slot>
          </div>
          <input
            ref="inputRef"
            v-overflow-tips="inputTooltipsConfig"
            class="dbm-select-input"
            :disabled="disabled"
            :placeholder="triggerPlaceholder"
            :readonly="!isInput"
            type="text"
            :value="triggerValue"
            @input="handleInputChange"
            @keydown.enter="handleTriggerEnter" />
        </div>
        <BkLoading
          v-if="loading"
          class="dbm-select-spinner"
          loading
          mode="spin"
          size="mini"
          theme="primary" />
        <Close
          v-else-if="showClear"
          class="dbm-select-clear-icon"
          @click="handleClear" />
        <span
          v-else-if="$slots.suffix"
          class="dbm-select-angle-down">
          <slot name="suffix" />
        </span>
        <AngleDown
          v-else
          class="dbm-select-angle-down" />
      </template>
    </div>
    <!-- 下拉内容：作为 tippy.js 挂载源，展示时被移动到 body（或就近父节点） -->
    <div style="display: none">
      <div
        ref="contentRef"
        class="dbm-select-popover"
        :class="popoverOptions?.extCls"
        :style="contentStyle">
        <div
          v-if="isShowAll"
          class="dbm-select-all">
          <div
            class="dbm-select-all-wrapper"
            :class="{
              'is-active': isAll,
              'is-disabled': showAllDisabled,
            }"
            @click="handleToggleAll">
            <slot name="allOptionIcon">
              <TextAll class="dbm-select-all-icon" />
            </slot>
            <span>{{ allOptionText || t('全部') }}</span>
          </div>
        </div>
        <div
          v-if="filterable && !inputSearch"
          class="dbm-select-search-wrapper">
          <Search
            class="dbm-select-search-icon"
            :height="16"
            :width="16" />
          <input
            ref="searchRef"
            v-model="searchValue"
            class="dbm-select-search-input"
            :placeholder="localSearchPlaceholder"
            type="text" />
          <span
            v-if="searchValue"
            class="dbm-select-search-clear"
            @click.stop.prevent="searchValue = ''">
            <Close />
          </span>
        </div>
        <div
          v-if="!isShowSelectContent"
          class="dbm-select-empty">
          <slot
            name="empty"
            :search-loading="searchLoading"
            :text="curContentText">
            <BkLoading
              v-if="searchLoading"
              class="dbm-select-loading-icon"
              loading
              mode="spin"
              size="mini"
              theme="primary" />
            <span>{{ curContentText }}</span>
          </slot>
        </div>
        <div class="dbm-select-content">
          <div
            v-show="isShowSelectContent"
            ref="scrollContainerRef"
            class="dbm-select-dropdown"
            :style="dropdownStyle"
            @scroll="handleScroll">
            <ul class="dbm-select-options">
              <li
                v-if="isShowSelectAll"
                class="dbm-select-option dbm-select-all-option"
                :class="{ 'is-disabled': showSelectAllDisabled }"
                @click="handleToggleSelectAll"
                @mouseenter="setActiveOptionValue('')">
                <BkCheckbox
                  v-if="showSelectedIcon"
                  class="dbm-select-checkbox"
                  :disabled="showSelectAllDisabled"
                  :indeterminate="!isAllSelected && !!selected.length"
                  :model-value="isAllSelected" />
                {{ localSelectAllText }}
              </li>
              <li
                v-if="virtualBlankTop"
                :style="{ height: `${virtualBlankTop}px` }" />
              <Option
                v-for="item in visibleOptionList"
                :id="item[idKey]"
                :key="item[idKey]"
                :disabled="!!item.disabled"
                :name="item[displayKey]"
                :skip-register="isEnableVirtualRender">
                <template
                  v-if="$slots.optionRender"
                  #default>
                  <slot
                    :item="item"
                    name="optionRender" />
                </template>
              </Option>
              <li
                v-if="virtualBlankBottom"
                :style="{ height: `${virtualBlankBottom}px` }" />
              <slot />
              <li
                v-if="scrollLoading"
                class="dbm-select-options-loading">
                <BkLoading
                  class="dbm-select-loading-icon"
                  loading
                  mode="spin"
                  size="mini"
                  theme="primary" />
                <span>{{ localLoadingText }}</span>
              </li>
            </ul>
          </div>
          <div
            v-if="$slots.extension"
            class="dbm-select-extension">
            <slot name="extension" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { AngleDown, Close, Search, TextAll } from 'bkui-vue/lib/icon';
  import { useFormItem } from 'bkui-vue/lib/shared';
  import { isEqual } from 'lodash';
  import pinyin from 'tiny-pinyin';
  import tippy, { type Instance, type Placement, type SingleTarget } from 'tippy.js';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import {
    isInViewPort,
    type OptionRegistry,
    type OptionValue,
    type SelectedItem,
    selectKey,
    toLowerCase,
  } from './common';
  import Option from './components/Option.vue';
  import TagTrigger from './components/TagTrigger.vue';

  interface PopoverOptions {
    /** 兼容 bk-select 的写法；tippy 在 disableTeleport 下就近挂载已覆盖该语义，此处不单独处理 */
    boundary?: string;
    /** 不使用 teleport，下拉内容就近挂载在组件内部，随父容器滚动 */
    disableTeleport?: boolean;
    extCls?: string;
    offset?: number;
    placement?: Placement;
    width?: number | string;
    zIndex?: number;
  }

  interface Props {
    /** 「全部」选项对应的值 */
    allOptionId?: OptionValue;
    allOptionText?: string;
    /** 是否允许输入选项之外的值 */
    allowCreate?: boolean;
    /** 可以作为有效选中值的空值，如 [0]、[''] */
    allowEmptyValues?: OptionValue[];
    autoFocus?: boolean;
    /** collapseTags 模式下，展开下拉时自动展开全部标签 */
    autoHeight?: boolean;
    behavior?: 'normal' | 'simplicity';
    clearable?: boolean;
    /** 多选标签超出一行时合并为 +N */
    collapseTags?: boolean;
    /** 自定义下拉内容，此时不再展示无数据 / 无匹配数据 */
    customContent?: boolean;
    disabled?: boolean;
    disableFocusBehavior?: boolean;
    disableScrollToSelectedOption?: boolean;
    /** list 模式下取展示文案的字段名 */
    displayKey?: string;
    /** 是否开启虚拟滚动，仅 list 模式生效 */
    enableVirtualRender?: boolean;
    filterable?: boolean;
    filterOption?: (searchValue: string, item: Record<string, OptionValue>) => boolean;
    highlightKeyword?: boolean;
    /** list 模式下取值的字段名 */
    idKey?: string;
    /** 搜索框是否直接使用触发器输入框 */
    inputSearch?: boolean;
    /** 透传触发器输入框的 tooltips 配置 */
    inputTooltipsOptions?: Record<string, OptionValue>;
    /** 收起下拉时是否保留搜索内容 */
    keepSearchValue?: boolean;
    list?: Record<string, OptionValue>[];
    loading?: boolean;
    loadingText?: string;
    minHeight?: number;
    modelValue?: OptionValue;
    multiple?: boolean;
    multipleMode?: 'default' | 'tag';
    noDataText?: string;
    noMatchText?: string;
    placeholder?: string;
    popoverMinWidth?: number;
    popoverOptions?: PopoverOptions;
    prefix?: string;
    remoteMethod?: (value: string) => Promise<unknown> | unknown;
    /** 下拉区域最大高度 */
    scrollHeight?: number;
    scrollLoading?: boolean;
    searchPlaceholder?: string;
    searchWithPinyin?: boolean;
    selectAllText?: string;
    showAll?: boolean;
    showAllDisabled?: boolean;
    showOnInit?: boolean;
    showSelectAll?: boolean;
    showSelectAllDisabled?: boolean;
    showSelectedIcon?: boolean;
    size?: 'small' | 'default' | 'large' | 'huge';
    tagTheme?: '' | 'danger' | 'info' | 'success' | 'warning';
    /** manual 时展开 / 收起完全由外部通过 ref 控制 */
    trigger?: 'default' | 'manual';
    withValidate?: boolean;
  }

  // value 声明为 any，与原 bk-select 运行时 emits 的类型表现对齐，避免业务侧处理器参数逆变报错
  interface Emits {
    (e: 'change' | 'update:modelValue', value: any, oldValue: any): void;
    (e: 'clear', value: any): void;
    (e: 'deselect' | 'select' | 'tag-remove', value: any): void;
    (e: 'blur' | 'focus'): void;
    (e: 'scroll-end'): void;
    (e: 'search-change', value: string): void;
    (e: 'toggle', isShow: boolean): void;
  }

  interface Exposes {
    blur: () => void;
    focus: () => void;
    hidePopover: () => void;
    showPopover: () => void;
  }

  defineOptions({
    name: 'Select',
  });

  const props = withDefaults(defineProps<Props>(), {
    allOptionId: undefined,
    allOptionText: '',
    allowCreate: false,
    allowEmptyValues: () => [],
    autoFocus: false,
    autoHeight: true,
    behavior: 'normal',
    clearable: true,
    collapseTags: false,
    customContent: false,
    disabled: false,
    disableFocusBehavior: false,
    disableScrollToSelectedOption: false,
    displayKey: 'label',
    enableVirtualRender: false,
    filterable: false,
    filterOption: undefined,
    highlightKeyword: false,
    idKey: 'value',
    inputSearch: false,
    inputTooltipsOptions: () => ({}),
    keepSearchValue: false,
    list: () => [],
    loading: false,
    loadingText: undefined,
    minHeight: undefined,
    modelValue: undefined,
    multiple: false,
    multipleMode: 'default',
    noDataText: undefined,
    noMatchText: undefined,
    placeholder: undefined,
    popoverMinWidth: 0,
    popoverOptions: undefined,
    prefix: '',
    remoteMethod: undefined,
    scrollHeight: 204,
    scrollLoading: false,
    searchPlaceholder: undefined,
    searchWithPinyin: true,
    selectAllText: undefined,
    showAll: false,
    showAllDisabled: false,
    showOnInit: false,
    showSelectAll: false,
    showSelectAllDisabled: false,
    showSelectedIcon: true,
    size: 'default',
    tagTheme: '',
    trigger: 'default',
    withValidate: true,
  });

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    allOptionIcon?: () => VNode;
    default?: () => VNode;
    empty?: (props: { searchLoading: boolean; text: string }) => VNode;
    extension?: () => VNode;
    optionRender?: (props: { item: Record<string, OptionValue> }) => VNode;
    prefix?: () => VNode;
    suffix?: () => VNode;
    tag?: (props: { selected: SelectedItem[] }) => VNode;
    tagRender?: (props: SelectedItem) => VNode;
    trigger?: (props: { selected: SelectedItem[] }) => VNode;
  }>();

  // 单行选项高度，用于虚拟滚动的位置换算
  const VIRTUAL_LINE_HEIGHT = 32;
  // 虚拟滚动上下各多渲染的行数，避免快速滚动露白
  const VIRTUAL_BUFFER_COUNT = 5;

  const { t } = useI18n();

  const formItem = useFormItem();

  const rootRef = useTemplateRef('rootRef');
  const triggerRef = useTemplateRef('triggerRef');
  const contentRef = useTemplateRef('contentRef');
  const inputRef = useTemplateRef('inputRef');
  const searchRef = useTemplateRef('searchRef');
  const scrollContainerRef = useTemplateRef('scrollContainerRef');
  const tagTriggerRef = useTemplateRef('tagTriggerRef');

  const optionsMap = ref(new Map<OptionValue, OptionRegistry>());
  const selected = ref<SelectedItem[]>([]);
  const activeOptionValue = ref<OptionValue>('');
  const searchValue = ref('');
  // 触发器输入框内容，用于 inputSearch 搜索与 allowCreate 创建
  const customOptionName = ref('');
  const searchLoading = ref(false);
  const isPopoverShow = ref(false);
  const isFocus = ref(false);
  const isHover = ref(false);
  const triggerWidth = ref(0);
  const virtualStartIndex = ref(0);

  let tippyInstance: Instance | undefined;
  let resizeObserver: ResizeObserver | undefined;
  // 当前是否已滚动到底部，用于 scroll-end 去重
  let isScrollBottom = false;

  const localPlaceholder = computed(() => props.placeholder ?? t('请选择'));
  const localSearchPlaceholder = computed(() => props.searchPlaceholder ?? t('请输入关键字'));
  const localSelectAllText = computed(() => props.selectAllText ?? t('全选'));
  const localLoadingText = computed(() => props.loadingText ?? t('加载中'));

  // 仅用于拦截交互：loading 期间不响应展开 / 选中，但外观（禁用底色、聚焦边框）只跟随 disabled，
  // 否则 remoteMethod 每次请求都会让触发器在禁用态与聚焦态之间闪烁
  const isDisabled = computed(() => props.disabled || props.loading);

  const hasPrefix = computed(() => !!props.prefix || !!slots.prefix);

  const curSearchValue = computed(() => searchValue.value || customOptionName.value);

  const isRemoteSearch = computed(() => props.filterable && typeof props.remoteMethod === 'function');

  const options = computed(() => [...optionsMap.value.values()].sort((cur, next) => cur.order - next.order));

  const listMap = computed(() =>
    props.list.reduce<Record<string, OptionValue>>((result, item) => {
      Object.assign(result, { [item[props.idKey]]: item[props.displayKey] });
      return result;
    }, {}),
  );

  // 已选值上一次的展示文案，用于选项尚未渲染时的回显兜底
  const selectedCacheMap = computed(() =>
    selected.value.reduce<Record<string, number | string>>(
      (result, item) => {
        Object.assign(result, { [item.value]: item.label });
        return result;
      },
      { [String(props.allOptionId)]: props.allOptionText || t('全部') },
    ),
  );

  /** 展示文案优先级：已注册选项 > list 数据 > 上一次选中的文案 > 值本身 */
  const getLabelByValue = (value: OptionValue) => {
    let optionKey = value;
    // 选项值为对象时引用可能已变更，需要按值找回注册时的 key
    if (typeof optionKey === 'object' && optionKey !== null) {
      for (const key of optionsMap.value.keys()) {
        if (isEqual(key, optionKey)) {
          optionKey = key;
          break;
        }
      }
    }
    return (
      optionsMap.value.get(optionKey)?.optionName ??
      listMap.value[optionKey] ??
      selectedCacheMap.value[optionKey] ??
      optionKey
    );
  };

  const selectedTags = computed(() =>
    selected.value.map((item) => ({
      label: getLabelByValue(item.value),
      value: item.value,
    })),
  );

  const selectedLabel = computed(() => selectedTags.value.map((item) => String(item.label)));

  /** 默认搜索规则：自定义过滤 > 拼音（全拼 / 首字母）或文案包含 > 文案包含 */
  const isSearchMatched = (searchKeyword: string, optionName: string, filterData: Record<string, OptionValue> = {}) => {
    if (props.filterOption) {
      return !!props.filterOption(searchKeyword, { ...filterData });
    }
    const keyword = toLowerCase(searchKeyword);
    if (props.searchWithPinyin) {
      const pinyinList = pinyin
        .parse(optionName)
        .map((item) => (item.type === 2 ? item.target.toLowerCase() : item.target));
      const initials = pinyinList.reduce((result, item) => result + item[0], '');
      if (pinyinList.join('').includes(keyword) || initials.includes(keyword)) {
        return true;
      }
    }
    return toLowerCase(optionName).includes(keyword);
  };

  // list 模式下的搜索结果；远程搜索时 list 由外部更新，不在本地过滤
  const filterList = computed(() => {
    if (isRemoteSearch.value || !curSearchValue.value) {
      return props.list;
    }
    return props.list.filter((item) => isSearchMatched(curSearchValue.value, String(item[props.displayKey]), item));
  });

  const isOptionsEmpty = computed(() => (props.list.length ? false : !options.value.length));

  const isSearchEmpty = computed(() => {
    if (props.list.length) {
      return !!curSearchValue.value && !filterList.value.length;
    }
    return !!options.value.length && options.value.every((option) => !option.visible);
  });

  const isShowSelectContent = computed(() => {
    if (props.customContent) {
      return true;
    }
    return !(searchLoading.value || isOptionsEmpty.value || isSearchEmpty.value);
  });

  const isShowSelectAll = computed(
    () => props.multiple && props.showSelectAll && (!curSearchValue.value || !props.filterable),
  );

  const isShowAll = computed(() => props.multiple && props.showAll);

  const isAll = computed(() => selected.value.length === 1 && selected.value[0]?.value === props.allOptionId);

  /** 可选中的值集合（排除禁用项），list 与 option 两种数据来源合并去重 */
  const selectableList = computed(() => {
    const result = new Map<OptionValue, number | string>();
    options.value.forEach((option) => {
      if (option.isDisabled || result.has(option.optionID)) {
        return;
      }
      result.set(option.optionID, option.optionName);
    });
    props.list.forEach((item) => {
      if (item.disabled || result.has(item[props.idKey])) {
        return;
      }
      result.set(item[props.idKey], item[props.displayKey]);
    });
    return result;
  });

  const isAllSelected = computed(() => {
    if (!selectableList.value.size) {
      return false;
    }
    return [...selectableList.value.keys()].every((value) => selected.value.some((item) => isEqual(item.value, value)));
  });

  const curContentText = computed(() => {
    if (searchLoading.value) {
      return localLoadingText.value;
    }
    if (isSearchEmpty.value) {
      return props.noMatchText ?? t('无匹配数据');
    }
    if (isOptionsEmpty.value) {
      return props.noDataText ?? t('无数据');
    }
    return '';
  });

  // 触发器输入框可编辑：inputSearch 搜索（展开时）或 allowCreate 创建
  const isInput = computed(() => (props.filterable && props.inputSearch && isPopoverShow.value) || props.allowCreate);

  const isCollapseTags = computed(() =>
    props.autoHeight ? props.collapseTags && !isPopoverShow.value : props.collapseTags,
  );

  const showClear = computed(() => {
    if (isDisabled.value || !isHover.value) {
      return false;
    }
    return (props.clearable && !!selected.value.length) || (props.allowCreate && !!customOptionName.value);
  });

  const triggerValue = computed(() =>
    isInput.value && customOptionName.value ? customOptionName.value : selectedLabel.value.join(','),
  );

  const triggerPlaceholder = computed(() =>
    isInput.value ? selectedLabel.value.join(',') || localPlaceholder.value : localPlaceholder.value,
  );

  const inputTooltipsConfig = computed(() => ({
    content: selectedLabel.value.join(','),
    ...props.inputTooltipsOptions,
  }));

  // collapseTags 展开标签时标签区会溢出容器，触发器保持 32px 以免撑开外部布局
  const triggerStyle = computed(() => (props.collapseTags ? { height: '32px' } : {}));

  const contentStyle = computed(() => {
    const { width } = props.popoverOptions ?? {};
    if (width !== undefined) {
      return { width: typeof width === 'number' ? `${width}px` : width };
    }
    return { width: `${Math.max(triggerWidth.value, props.popoverMinWidth)}px` };
  });

  const dropdownStyle = computed(() => ({
    maxHeight: `${props.scrollHeight}px`,
    minHeight: props.minHeight ? `${props.minHeight}px` : undefined,
  }));

  // 虚拟滚动可视高度：扣除选项列表的上下内边距与置顶的全选行
  const virtualHeight = computed(() => props.scrollHeight - 8 - (isShowSelectAll.value ? VIRTUAL_LINE_HEIGHT : 0));

  const isEnableVirtualRender = computed(
    () => props.enableVirtualRender && filterList.value.length * VIRTUAL_LINE_HEIGHT > virtualHeight.value,
  );

  const virtualStart = computed(() => Math.max(0, virtualStartIndex.value - VIRTUAL_BUFFER_COUNT));

  const virtualEnd = computed(() =>
    Math.min(
      filterList.value.length,
      virtualStartIndex.value + Math.ceil(virtualHeight.value / VIRTUAL_LINE_HEIGHT) + VIRTUAL_BUFFER_COUNT,
    ),
  );

  const visibleOptionList = computed(() =>
    isEnableVirtualRender.value ? filterList.value.slice(virtualStart.value, virtualEnd.value) : filterList.value,
  );

  const virtualBlankTop = computed(() => (isEnableVirtualRender.value ? virtualStart.value * VIRTUAL_LINE_HEIGHT : 0));

  const virtualBlankBottom = computed(() =>
    isEnableVirtualRender.value ? (filterList.value.length - virtualEnd.value) * VIRTUAL_LINE_HEIGHT : 0,
  );

  // 键盘导航与滚动定位的候选项，已排除禁用与被搜索过滤掉的选项
  const navigableList = computed<{ getEl?: () => HTMLElement | null; value: OptionValue }[]>(() => {
    if (isEnableVirtualRender.value) {
      return filterList.value.filter((item) => !item.disabled).map((item) => ({ value: item[props.idKey] }));
    }
    return options.value
      .filter((option) => option.visible && !option.isDisabled)
      .map((option) => ({ getEl: option.getEl, value: option.optionID }));
  });

  const register = (key: OptionValue, option: OptionRegistry) => {
    optionsMap.value.set(key, option);
  };

  const unregister = (key: OptionValue, option?: OptionRegistry) => {
    // 选项值变更会先注册新值再注销旧值，注销时需确认持有者未被替换
    if (option && optionsMap.value.get(key) !== option) {
      return;
    }
    optionsMap.value.delete(key);
  };

  const setActiveOptionValue = (value: OptionValue) => {
    activeOptionValue.value = value;
  };

  /**
   * 空值不计入已选项，避免 ''、null 之类的值被回显成一个空标签。
   * 0 一律视为有效值，其余空值需要调用方通过 allowEmptyValues 显式声明
   */
  const isValidValue = (value: OptionValue) => !!value || value === 0 || props.allowEmptyValues.includes(value);

  /** 以 modelValue 为准重置已选数据 */
  const handleSetSelectedData = () => {
    const valueList = Array.isArray(props.modelValue) ? props.modelValue : [props.modelValue];
    const nextSelected: SelectedItem[] = valueList
      .filter(isValidValue)
      .map((value) => ({ label: getLabelByValue(value), value }));
    // 选项异步渲染时会多次触发，内容一致则不再写入，避免多余更新
    if (!isEqual(nextSelected, selected.value)) {
      selected.value = nextSelected;
    }
  };

  const emitChange = (value: OptionValue) => {
    if (value === props.modelValue) {
      return;
    }
    emits('update:modelValue', value, props.modelValue);
    emits('change', value, props.modelValue);
  };

  const emitSelectedChange = () => {
    emitChange(selected.value.map((item) => item.value));
  };

  const handleFocus = () => {
    if (isFocus.value) {
      return;
    }
    isFocus.value = true;
    emits('focus');
  };

  const focusInput = () => {
    if (props.disableFocusBehavior) {
      return;
    }
    setTimeout(() => {
      if (props.filterable && !props.inputSearch) {
        searchRef.value?.focus();
        return;
      }
      if (props.multipleMode === 'tag') {
        tagTriggerRef.value?.focus();
        return;
      }
      inputRef.value?.focus();
    });
  };

  const blurInput = () => {
    setTimeout(() => {
      if (props.multipleMode === 'tag') {
        tagTriggerRef.value?.blur();
        return;
      }
      inputRef.value?.blur();
    });
  };

  const handleBlur = () => {
    if (!isFocus.value) {
      return;
    }
    isFocus.value = false;
    blurInput();
    emits('blur');
  };

  const showPopover = () => {
    isPopoverShow.value = true;
  };

  const hidePopover = () => {
    isPopoverShow.value = false;
  };

  // trigger 为 manual 时，展开 / 收起只接受外部通过 ref 调用
  const handleShowPopover = () => {
    if (props.trigger === 'manual') {
      return;
    }
    showPopover();
  };

  const handleHidePopover = () => {
    if (props.trigger === 'manual') {
      return;
    }
    hidePopover();
  };

  const handleTogglePopover = () => {
    if (isDisabled.value || props.trigger === 'manual') {
      return;
    }
    handleFocus();
    isPopoverShow.value = !isPopoverShow.value;
  };

  const scrollOptionIntoView = (index: number) => {
    const container = scrollContainerRef.value;
    if (index < 0 || !container) {
      return;
    }
    if (isEnableVirtualRender.value) {
      const offsetTop = index * VIRTUAL_LINE_HEIGHT + (isShowSelectAll.value ? VIRTUAL_LINE_HEIGHT : 0);
      if (offsetTop < container.scrollTop) {
        container.scrollTop = offsetTop;
      } else if (offsetTop + VIRTUAL_LINE_HEIGHT > container.scrollTop + container.clientHeight) {
        container.scrollTop = offsetTop + VIRTUAL_LINE_HEIGHT - container.clientHeight;
      }
      return;
    }
    const el = navigableList.value[index]?.getEl?.();
    if (el && !isInViewPort(el, container)) {
      el.scrollIntoView({ block: 'nearest' });
    }
  };

  /** 展开下拉时默认高亮首个已选项，无已选则高亮第一个可选项 */
  const initActiveOptionValue = () => {
    const availableList = navigableList.value;
    if (!availableList.length) {
      activeOptionValue.value = '';
      return;
    }
    const firstSelected = selected.value[0]?.value;
    const isSelectable = availableList.some((item) => isEqual(item.value, firstSelected));
    activeOptionValue.value = isSelectable ? firstSelected : availableList[0].value;
  };

  const scrollActiveOptionIntoView = () => {
    if (props.disableScrollToSelectedOption) {
      return;
    }
    scrollOptionIntoView(navigableList.value.findIndex((item) => isEqual(item.value, activeOptionValue.value)));
  };

  const handleOptionSelected = (option: { optionID: OptionValue; optionName?: number | string }) => {
    if (isDisabled.value || !option) {
      return;
    }
    // 选中具体选项时移除「全部」
    const allOptionIndex = selected.value.findIndex((item) => item.value === props.allOptionId);
    if (allOptionIndex > -1) {
      selected.value.splice(allOptionIndex, 1);
    }
    const label = option.optionName || option.optionID;
    if (!props.multiple) {
      selected.value = [{ label, value: option.optionID }];
      emitChange(option.optionID);
      emits('select', option.optionID);
      handleHidePopover();
      handleBlur();
      return;
    }
    const index = selected.value.findIndex((item) => isEqual(item.value, option.optionID));
    if (index > -1) {
      selected.value.splice(index, 1);
      emitSelectedChange();
      emits('deselect', option.optionID);
    } else {
      selected.value.push({ label, value: option.optionID });
      emitSelectedChange();
      emits('select', option.optionID);
    }
    focusInput();
  };

  const handleToggleSelectAll = () => {
    if (props.showSelectAllDisabled) {
      return;
    }
    if (isAllSelected.value) {
      selected.value = [];
    } else {
      selected.value = [...selectableList.value.entries()].map(([value, label]) => ({ label, value }));
    }
    emitSelectedChange();
    focusInput();
  };

  const handleToggleAll = () => {
    if (props.showAllDisabled) {
      return;
    }
    selected.value = isAll.value ? [] : [{ label: props.allOptionText || t('全部'), value: props.allOptionId }];
    emitSelectedChange();
    focusInput();
  };

  const handleClear = (event: MouseEvent) => {
    event.stopPropagation();
    selected.value = [];
    customOptionName.value = '';
    emitChange(props.multiple ? [] : '');
    emits('clear', props.multiple ? [] : '');
    handleHidePopover();
    handleBlur();
  };

  const handleDeleteTag = (value: OptionValue) => {
    if (isDisabled.value) {
      return;
    }
    const index = selected.value.findIndex((item) => isEqual(item.value, value));
    if (index > -1) {
      selected.value.splice(index, 1);
      emitSelectedChange();
      emits('tag-remove', value);
    }
  };

  const handleInputChange = (event: Event) => {
    customOptionName.value = (event.target as HTMLInputElement).value;
  };

  /** allowCreate：回车创建选项之外的值 */
  const handleCreateCustomOption = (value: number | string, event: KeyboardEvent) => {
    const customValue = String(value).trim();
    if (!props.allowCreate || !customValue) {
      return;
    }
    event.stopPropagation();
    event.preventDefault();
    const matchedOption = options.value.find((item) => toLowerCase(item.optionName) === toLowerCase(customValue));
    // 输入内容与已有选项一致时直接选中，不再创建
    if (matchedOption) {
      handleOptionSelected(matchedOption);
      customOptionName.value = '';
      return;
    }
    if (props.multiple) {
      if (selected.value.every((item) => item.value !== customValue)) {
        selected.value.push({ label: customValue, value: customValue });
        emitSelectedChange();
      }
      customOptionName.value = '';
      return;
    }
    selected.value = [{ label: customValue, value: customValue }];
    emitChange(customValue);
    handleHidePopover();
  };

  const handleTriggerEnter = (event: KeyboardEvent) => {
    handleCreateCustomOption((event.target as HTMLInputElement).value, event);
  };

  const handleScroll = (event: Event) => {
    const { clientHeight, scrollHeight, scrollTop } = event.target as HTMLElement;
    if (isEnableVirtualRender.value) {
      const selectAllHeight = isShowSelectAll.value ? VIRTUAL_LINE_HEIGHT : 0;
      virtualStartIndex.value = Math.max(0, Math.floor((scrollTop - selectAllHeight) / VIRTUAL_LINE_HEIGHT));
    }
    // 滚动到底部触发加载更多，1px 容差用于抵消缩放导致的小数误差
    const isBottom = scrollTop + clientHeight >= scrollHeight - 1;
    // 停留在底部期间只触发一次，避免小数级滚动重复分页
    if (isBottom && !isScrollBottom) {
      emits('scroll-end');
    }
    isScrollBottom = isBottom;
  };

  const handleDocumentKeydown = (event: KeyboardEvent) => {
    const availableList = navigableList.value;
    switch (event.code) {
      case 'ArrowDown':
      case 'ArrowUp': {
        // 阻止方向键滚动页面
        event.preventDefault();
        if (!availableList.length) {
          return;
        }
        const index = availableList.findIndex((item) => isEqual(item.value, activeOptionValue.value));
        const nextIndex =
          event.code === 'ArrowDown'
            ? (index + 1) % availableList.length
            : (index <= 0 ? availableList.length : index) - 1;
        activeOptionValue.value = availableList[nextIndex].value;
        scrollOptionIntoView(nextIndex);
        break;
      }
      // 多选时回退键删除最后一个已选项，输入框有内容或在下拉搜索框内时不处理
      case 'Backspace': {
        if (!props.multiple || !selected.value.length || curSearchValue.value || event.target === searchRef.value) {
          return;
        }
        selected.value.pop();
        emitSelectedChange();
        break;
      }
      case 'Enter':
      case 'NumpadEnter': {
        const target = event.target as HTMLInputElement;
        // 自定义创建的回车由 handleCreateCustomOption 处理
        if (props.allowCreate && target?.value) {
          return;
        }
        // 下拉搜索框内已有关键字时，回车只用于确认搜索，不选中高亮项
        if (target === searchRef.value && target?.value) {
          return;
        }
        if (activeOptionValue.value === '' || activeOptionValue.value === undefined) {
          return;
        }
        handleOptionSelected({
          optionID: activeOptionValue.value,
          optionName: getLabelByValue(activeOptionValue.value),
        });
        break;
      }
      case 'Escape': {
        handleHidePopover();
        handleBlur();
        break;
      }
      default:
        break;
    }
  };

  const handleDocumentClick = (event: MouseEvent) => {
    const target = event.target as Node;
    if (rootRef.value?.contains(target) || tippyInstance?.popper.contains(target)) {
      return;
    }
    handleHidePopover();
    handleBlur();
  };

  // 校验跟随 modelValue 变化，外部程序化赋值（表单回填 / 重置）同样需要清掉已有的报错
  watch(
    () => props.modelValue,
    () => {
      handleSetSelectedData();
      if (props.withValidate) {
        formItem?.validate?.('change');
      }
    },
    {
      deep: true,
    },
  );

  // list 异步返回后需要补全已选项的展示文案
  watch(() => props.list, handleSetSelectedData);

  // 搜索：远程搜索交给外部方法，本地搜索按关键字回写各选项的可见性
  watch(curSearchValue, async (keyword) => {
    emits('search-change', keyword);
    virtualStartIndex.value = 0;
    isScrollBottom = false;
    if (scrollContainerRef.value) {
      scrollContainerRef.value.scrollTop = 0;
    }
    searchLoading.value = isRemoteSearch.value;
    try {
      if (isRemoteSearch.value) {
        await props.remoteMethod?.(keyword);
      } else if (props.filterable) {
        for (const option of optionsMap.value.values()) {
          option.visible = keyword ? isSearchMatched(keyword, String(option.optionName), { ...option }) : true;
        }
      }
    } finally {
      searchLoading.value = false;
      initActiveOptionValue();
    }
  });

  watch(isPopoverShow, (isShow) => {
    emits('toggle', isShow);
    if (!isShow) {
      tippyInstance?.hide();
      if (!props.keepSearchValue) {
        searchValue.value = '';
        // 触发器输入框作为搜索框时同样需要清空，否则收起后仍在过滤选项
        if (props.filterable && props.inputSearch && !props.allowCreate) {
          customOptionName.value = '';
        }
      }
      document.removeEventListener('keydown', handleDocumentKeydown);
      document.removeEventListener('click', handleDocumentClick);
      return;
    }
    tippyInstance?.show();
    document.addEventListener('keydown', handleDocumentKeydown);
    document.addEventListener('click', handleDocumentClick);
    nextTick(() => {
      focusInput();
      initActiveOptionValue();
      scrollActiveOptionIntoView();
      tippyInstance?.popperInstance?.update();
    });
  });

  // 下拉内容高度变化后重新计算浮层位置
  watch([selected, () => filterList.value.length, isShowSelectContent], () => {
    if (!isPopoverShow.value) {
      return;
    }
    nextTick(() => {
      tippyInstance?.popperInstance?.update();
    });
  });

  provide(
    selectKey,
    reactive({
      activeOptionValue,
      curSearchValue,
      handleOptionSelected,
      highlightKeyword: computed(() => props.highlightKeyword),
      isSearchEmpty,
      multiple: computed(() => props.multiple),
      register,
      selected,
      setActiveOptionValue,
      showSelectedIcon: computed(() => props.showSelectedIcon),
      unregister,
    }),
  );

  onMounted(() => {
    handleSetSelectedData();

    if (triggerRef.value) {
      triggerWidth.value = triggerRef.value.offsetWidth;
      resizeObserver = new ResizeObserver(([entry]) => {
        triggerWidth.value = entry.contentRect.width;
      });
      resizeObserver.observe(triggerRef.value);
    }

    if (triggerRef.value && contentRef.value) {
      const { disableTeleport, offset, placement, zIndex } = props.popoverOptions ?? {};
      tippyInstance = tippy(triggerRef.value as SingleTarget, {
        appendTo: () => (disableTeleport ? (rootRef.value ?? document.body) : document.body),
        arrow: false,
        content: contentRef.value,
        interactive: true,
        maxWidth: 'none',
        offset: [0, offset ?? 4],
        placement: placement ?? 'bottom-start',
        theme: 'db-select',
        trigger: 'manual',
        zIndex: zIndex ?? 9999,
      });
    }

    if (props.showOnInit) {
      handleShowPopover();
    } else if (props.autoFocus) {
      focusInput();
    }
  });

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleDocumentKeydown);
    document.removeEventListener('click', handleDocumentClick);
    resizeObserver?.disconnect();
    resizeObserver = undefined;
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.unmount();
      tippyInstance.destroy();
      tippyInstance = undefined;
    }
  });

  defineExpose<Exposes>({
    blur: blurInput,
    focus: focusInput,
    hidePopover,
    showPopover,
  });
</script>

<style lang="less">
  @import 'bkui-vue/lib/styles/themes/themes.less';

  .dbm-select {
    display: block;
    width: 100%;
    font-size: 12px;

    &.is-popover-show {
      .dbm-select-angle-down {
        transform: rotate(180deg);
      }
    }

    &.is-focus:not(.is-disabled) {
      .dbm-select-input-box,
      .dbm-select-tag {
        border-color: @primary-color;
        outline: 0;
        box-shadow: 0 0 3px 0 @input-shadow-color;
      }

      &.is-simplicity {
        .dbm-select-input-box,
        .dbm-select-tag {
          border-color: transparent;
          border-bottom-color: @primary-color;
          box-shadow: none;
        }
      }
    }

    &.is-small {
      .dbm-select-input-box {
        height: 26px;
      }
    }

    &.is-large {
      font-size: 14px;

      .dbm-select-input-box {
        height: 40px;
      }
    }

    &.is-huge {
      font-size: 14px;

      .dbm-select-input-box {
        height: 48px;
      }
    }

    &.is-disabled {
      .dbm-select-input-box {
        background-color: @input-disabled-bg;
        border-color: @disable-color;
      }

      .dbm-select-input {
        color: @gray-color;
        cursor: not-allowed;
      }
    }

    &.is-simplicity {
      .dbm-select-input-box {
        background-color: transparent;
        border-color: transparent;
        border-bottom-color: @input-border-color;

        &:hover {
          background-color: @input-block-color;
          border-color: transparent;
          border-bottom-color: @light-gray;
        }
      }
    }
  }

  .dbm-select-trigger {
    position: relative;

    .dbm-select-angle-down,
    .dbm-select-clear-icon,
    .dbm-select-spinner {
      position: absolute;
      top: 0;
      right: 4px;
      display: inline-flex;
      height: 100%;
      align-items: center;
      justify-content: center;
    }

    .dbm-select-angle-down {
      width: 20px;
      font-size: 20px;
      color: @gray-color;
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .dbm-select-clear-icon {
      width: 20px;
      font-size: 14px;
      color: @light-gray;
      cursor: pointer;

      &:hover {
        color: @gray-color;
      }
    }

    .dbm-select-spinner {
      right: 6px;
    }
  }

  .dbm-select-input-box {
    display: flex;
    width: 100%;
    height: 32px;
    color: @default-color;
    background-color: @white-color;
    border: 1px solid @light-gray;
    border-radius: 2px;
    box-sizing: border-box;
    align-items: center;
    transition: all 0.1s;

    &.has-prefix {
      .dbm-select-input {
        padding-left: 0;
      }
    }

    &:hover {
      border-color: @gray-color;
    }

    .dbm-select-input {
      width: 100%;
      height: 100%;
      padding: 0 28px 0 10px;
      overflow: hidden;
      font-size: inherit;
      color: @default-color;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
      background-color: transparent;
      border: none;
      outline: none;
      flex: 1;

      &::placeholder {
        color: @light-gray;
      }
    }
  }

  .dbm-select-prefix-area {
    display: flex;
    height: 100%;
    padding: 0 10px;
    margin-right: 10px;
    color: @default-color;
    background-color: @select-hover-color;
    border-right: 1px solid @light-gray;
    align-items: center;
  }

  // tippy 下拉容器：去除默认背景与内边距，样式交由内容区自行控制
  .tippy-box[data-theme~='db-select'] {
    background-color: transparent;

    .tippy-content {
      padding: 0;
    }
  }

  .dbm-select-popover {
    font-size: 12px;
    color: @default-color;
    background-color: @white-color;
    border: 1px solid @disable-color;
    border-radius: 2px;
    box-shadow: 0 2px 6px 0 rgb(0 0 0 / 10%);

    ul {
      padding: 0;
      margin: 0;
      font-weight: normal;
      list-style: none;
    }

    .dbm-select-empty {
      display: flex;
      height: 56px;
      color: @default-color;
      align-items: center;
      justify-content: center;
    }

    .dbm-select-loading-icon {
      display: flex;
      width: 14px;
      height: 14px;
      margin-right: 4px;
      font-size: 14px;
      color: @light-gray;
      align-items: center;
      justify-content: center;
    }

    .dbm-select-dropdown {
      overflow: auto;

      &::-webkit-scrollbar {
        width: 4px;
        height: 4px;
      }

      &::-webkit-scrollbar-thumb {
        background: #dde4eb;
        border-radius: 20px;
        box-shadow: inset 0 0 6px hsl(0deg 0% 80% / 30%);
      }
    }

    .dbm-select-options {
      padding: 4px 0;
    }

    .dbm-select-all-option {
      position: sticky;
      top: 0;
      z-index: 1;
      background-color: @white-color;
      border-bottom: 1px solid @border-color;
    }

    .dbm-select-options-loading {
      display: flex;
      height: 32px;
      align-items: center;
      justify-content: center;
    }

    .dbm-select-all {
      padding: 4px 0;
      border-bottom: 1px solid @border-color;

      .dbm-select-all-wrapper {
        display: flex;
        height: 32px;
        padding: 0 12px;
        color: @default-color;
        cursor: pointer;
        align-items: center;

        &:hover {
          background-color: @select-hover-color;
        }

        &.is-active {
          color: @primary-color;
          background-color: @select-active-color;
        }

        &.is-disabled {
          color: @light-gray;
          cursor: not-allowed;

          &:hover {
            background-color: transparent;
          }
        }
      }

      .dbm-select-all-icon {
        margin-right: 4px;
        font-size: 16px;
      }
    }

    .dbm-select-search-wrapper {
      display: flex;
      margin: 4px 8px 0;
      border-bottom: 1px solid @input-block-hover-color;
      align-items: center;

      .dbm-select-search-icon {
        margin-left: 2px;
        color: @gray-color;
      }

      .dbm-select-search-input {
        width: 100%;
        height: 32px;
        padding: 0 8px;
        color: @default-color;
        cursor: text;
        background-color: transparent;
        border: none;
        outline: none;
        flex: 1;

        &::placeholder {
          color: @light-gray;
        }
      }

      .dbm-select-search-clear {
        display: flex;
        width: 14px;
        height: 14px;
        margin-right: 2px;
        font-size: 14px;
        color: @light-gray;
        cursor: pointer;
        align-items: center;
        justify-content: center;

        &:hover {
          color: @gray-color;
        }
      }
    }

    .dbm-select-extension {
      display: flex;
      height: 40px;
      background-color: @input-disabled-bg;
      border-top: 1px solid @disable-color;
      border-radius: 0 0 2px 2px;
      align-items: center;
    }
  }
</style>
