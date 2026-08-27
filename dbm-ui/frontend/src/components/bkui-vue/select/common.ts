/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import type { InjectionKey } from 'vue';

// 选项值声明为 any，与原 bk-select 的 PropTypes.any 表现对齐：业务侧存在 string / number / 对象等取值，
// 收紧类型会导致 v-model 与 change 处理器在调用侧报错
export type OptionValue = any;

export interface OptionGroupContext {
  disabled: boolean;
  groupCollapse: boolean;
  register: (key: OptionValue, option: OptionRegistry) => void;
  unregister: (key: OptionValue, option?: OptionRegistry) => void;
}

/**
 * option 注册到 select / option-group 的信息，visible 由 select 在搜索时回写。
 * 根元素以函数形式暴露：注册信息存放在 reactive 中，而 reactive 会深层解包 DOM 类型
 * （本项目 tsconfig 的 types 未包含 @vue/runtime-dom 的 bail 声明），直接存元素会得到不兼容的类型
 */
export interface OptionRegistry {
  getEl: () => HTMLElement | null;
  isDisabled: boolean;
  optionID: OptionValue;
  optionName: number | string;
  order: number;
  visible: boolean;
}

export interface SelectContext {
  activeOptionValue: OptionValue;
  curSearchValue: string;
  handleOptionSelected: (option: { optionID: OptionValue; optionName?: number | string }) => void;
  highlightKeyword: boolean;
  isSearchEmpty: boolean;
  multiple: boolean;
  register: (key: OptionValue, option: OptionRegistry) => void;
  selected: SelectedItem[];
  setActiveOptionValue: (value: OptionValue) => void;
  showSelectedIcon: boolean;
  unregister: (key: OptionValue, option?: OptionRegistry) => void;
}

export interface SelectedItem {
  label: number | string;
  value: OptionValue;
}

export const optionGroupKey: InjectionKey<OptionGroupContext> = Symbol('DbOptionGroup');

export const selectKey: InjectionKey<SelectContext> = Symbol('DbSelect');

/** 关键字匹配统一去首尾空格并转小写 */
export const toLowerCase = (value: number | string = '') => String(value).trim().toLowerCase();

/** 判断元素是否完整落在滚动容器可视区域内 */
export const isInViewPort = (el?: HTMLElement, client?: HTMLElement) => {
  if (!el || !client) {
    return true;
  }
  const { bottom: elBottom, top: elTop } = el.getBoundingClientRect();
  const { bottom: clientBottom, top: clientTop } = client.getBoundingClientRect();
  return elTop >= clientTop && elBottom <= clientBottom;
};
