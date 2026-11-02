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

import { markPageChanged, popoverInjectKey } from '@utils';

/**
 * 标记当前组件所在的内容已被编辑（需在 setup 中调用）。
 * 渲染在 DbSideslider / DbDialog 内：置弹层状态；渲染在页面上：记到页面状态，
 * 弹层打开期间（如弹层提交后回填页面）也不会在弹层关闭时被还原掉。
 * 组件自己包了 DbSideslider / DbDialog、标记的是自己弹层里的内容时不要用它，直接置 window.changeConfirm
 */
export const useMarkChanged = () => {
  const isInPopover = inject(popoverInjectKey, false);

  return () => {
    if (isInPopover) {
      window.changeConfirm = true;
      return;
    }
    markPageChanged();
  };
};
