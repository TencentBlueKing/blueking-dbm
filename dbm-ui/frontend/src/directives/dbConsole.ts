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
import type { DirectiveBinding } from 'vue';

import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { checkDbConsole } from '@utils';

/**
 * 根据 function_controller 配置控制元素的显示与隐藏
 * @param {*} el
 * @returns
 */
function init(el: HTMLElement, binding: DirectiveBinding<ExtractedControllerDataKeys>) {
  const { value } = binding;

  if (!value || checkDbConsole(value)) {
    return;
  }

  // 不在 function_controller 范围内，用空节点替换
  const substitudeElement = document.createElement('span');
  const tempParentNode = document.createElement('node');
  el.parentNode?.replaceChild(substitudeElement, el);
  tempParentNode.appendChild(el);
}

export default {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    init(el, binding);
  },
};
