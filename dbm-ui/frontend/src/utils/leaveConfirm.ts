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

import InfoBox from 'bkui-vue/lib/info-box';
import type { InjectionKey } from 'vue';

import { t } from '@locales/index';

/**
 * DbSideslider / DbDialog 向内容 provide，DbForm / EditableTable 据此区分自己在弹层内还是在页面上
 */
export const popoverInjectKey: InjectionKey<true> = Symbol('popover');

/**
 * 打开中的 DbSideslider / DbDialog，按打开顺序排列，值为「把打开前的页面状态标记为已编辑」。
 * 弹层关闭时会把 window.changeConfirm 还原成打开前记录的页面状态，
 * 弹层打开期间页面被修改（如弹层提交后回填页面表单）必须改这份记录，否则关闭时会被还原掉
 */
const openedPopoverList: Array<() => void> = [];

// 登记打开中的弹层，返回注销方法（可重复调用）
export const registerOpenedPopover = (markPageChanged: () => void) => {
  openedPopoverList.push(markPageChanged);
  return () => {
    const index = openedPopoverList.indexOf(markPageChanged);
    if (index > -1) {
      openedPopoverList.splice(index, 1);
    }
  };
};

/**
 * 页面（不在弹层内）的内容被用户修改。
 * 没有弹层打开时直接置位；有弹层打开时 window.changeConfirm 是弹层的状态，改最外层弹层记录的页面状态
 */
export const markPageChanged = () => {
  const markOutermostPageChanged = openedPopoverList[0];
  if (!markOutermostPageChanged) {
    window.changeConfirm = true;
    return;
  }
  markOutermostPageChanged();
};

/**
 * 打开时页面已被编辑（window.changeConfirm 为 true）的 DbSideslider / DbDialog 实例。
 * 二者打开期间会把 window.changeConfirm 临时置为 'popover'，
 * 只看 window.changeConfirm 会漏掉弹层下面页面的未保存修改，关闭浏览器标签时需要合并判断
 */
const coveredChangedPages = new Set<symbol>();

export const markCoveredPageChanged = (key: symbol, changed: boolean) => {
  if (changed) {
    coveredChangedPages.add(key);
    return;
  }
  coveredChangedPages.delete(key);
};

// 页面或侧栏内容是否存在未保存的修改（关闭浏览器标签前判断）
export const hasUnsavedChange = () => window.changeConfirm === true || coveredChangedPages.size > 0;

export const leaveConfirm = (): Promise<boolean> => {
  if (!window.changeConfirm || window.changeConfirm === 'popover') {
    return Promise.resolve(true);
  }

  return new Promise((resolve, reject) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('离开'),
      content: t('离开将会导致未保存信息丢失'),
      onCancel: () => {
        reject(false);
      },
      onConfirm: () => {
        window.changeConfirm = false;
        resolve(true);
        return true;
      },
      title: t('确认离开当前页'),
    });
  });
};
