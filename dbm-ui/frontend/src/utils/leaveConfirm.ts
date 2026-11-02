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
import { type InjectionKey, nextTick, type Ref } from 'vue';
import { isNavigationFailure, type NavigationFailure, NavigationFailureType } from 'vue-router';

import { t } from '@locales/index';

/**
 * DbSideslider / DbDialog 向内容 provide，DbForm / EditableTable 据此区分自己在弹层内还是在页面上
 */
export const popoverInjectKey: InjectionKey<true> = Symbol('popover');

/**
 * DbSideslider / DbDialog 向内容 provide 自身的显示状态。
 * render-directive 为 show（BkDialog 默认）时内容不随关闭卸载，DbForm / EditableTable 的「用户操作过」标记会保留到下次打开，
 * 下次打开时调用方重置表单数据就会被当成用户修改；内容据此在关闭时清掉标记
 */
export const popoverShowInjectKey: InjectionKey<Readonly<Ref<boolean>>> = Symbol('popover-show');

/**
 * 打开中的 DbSideslider / DbDialog，按打开顺序排列。
 * 弹层关闭时会把 window.changeConfirm 还原成打开前记录的页面状态，
 * 弹层打开期间页面被修改（如弹层提交后回填页面表单）必须改这份记录，否则关闭时会被还原掉；
 * 路由离开后页面已不存在，记录要清空，否则弹层随页面卸载时会把旧页面的已编辑状态还原到新页面
 */
interface OpenedPopover {
  // 把打开前记录的页面状态标记为已编辑
  markPageChanged: () => void;
  // 把打开前记录的页面状态清为未编辑
  resetPageChanged: () => void;
}

const openedPopoverList: OpenedPopover[] = [];

// 登记打开中的弹层，返回注销方法（可重复调用）
export const registerOpenedPopover = (popover: OpenedPopover) => {
  openedPopoverList.push(popover);
  return () => {
    const index = openedPopoverList.indexOf(popover);
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
  const outermostPopover = openedPopoverList[0];
  if (!outermostPopover) {
    window.changeConfirm = true;
    return;
  }
  outermostPopover.markPageChanged();
};

/**
 * 可撤销的编辑来源（DbForm、EditableTable 等），值为是否在弹层内。
 * 离开确认只有一个全局标志，多个来源同时置位时，其中一个卸载或复位不能清掉其它来源的未保存状态
 */
const changeSources = new Map<symbol, boolean>();

// 标记来源已编辑：弹层内置弹层状态，页面上记到页面状态
export const markSourceChanged = (source: symbol, isInPopover: boolean) => {
  changeSources.set(source, isInPopover);
  if (isInPopover) {
    window.changeConfirm = true;
    return;
  }
  markPageChanged();
};

/**
 * 撤销来源的编辑状态（卸载、退出编辑、弹层关闭时调用）。
 * 同范围（页面 / 弹层）还有其它来源已编辑时保持不动；页面上的来源在弹层打开期间撤销时，改最外层弹层记录的页面状态
 */
export const releaseSourceChanged = (source: symbol) => {
  if (!changeSources.has(source)) {
    return;
  }
  const isInPopover = changeSources.get(source);
  changeSources.delete(source);
  if ([...changeSources.values()].some((item) => item === isInPopover)) {
    return;
  }
  const outermostPopover = openedPopoverList[0];
  if (isInPopover || !outermostPopover) {
    window.changeConfirm = false;
    return;
  }
  outermostPopover.resetPageChanged();
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

/**
 * 离开页面后清空全部离开确认状态：全局标志、被弹层遮住的已编辑页面、打开中弹层记录的页面状态。
 * 页面上手动置 true 的组件没有卸载复位，路由离开时由这里统一复位
 */
export const resetChangeConfirm = () => {
  window.changeConfirm = false;
  coveredChangedPages.clear();
  changeSources.clear();
  openedPopoverList.forEach((item) => item.resetPageChanged());
};

// 离开确认框，确认离开返回 true，取消（含点关闭图标）返回 false
const openLeaveConfirmBox = () =>
  new Promise<boolean>((resolve) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('离开'),
      content: t('离开将会导致未保存信息丢失'),
      onCancel: () => {
        resolve(false);
      },
      onConfirm: () => {
        resolve(true);
        return true;
      },
      title: t('确认离开当前页'),
    });
  });

/**
 * 路由离开确认：页面、弹层内容、被弹层遮住的页面任一有未保存修改时弹确认，返回是否允许离开。
 * 这里不清状态：后续守卫仍可能取消导航，页面留下时修改要继续被拦截；导航完成后由 afterEach 调 resetChangeConfirm
 */
export const routeLeaveConfirm = async () => {
  if (!hasUnsavedChange()) {
    return true;
  }
  return openLeaveConfirmBox();
};

/**
 * 页面内切换选项（单据类型、架构类型等）跳转到同族页面时使用。
 * 切换的选项通常在 DbForm 内，选项变化本身会被记为修改；等这轮渲染更新（DbForm 置位）后还原为切换前的状态再跳转，
 * 只有切换前已有修改才弹离开确认。必须在选项变化的同一轮同步调用（@change / 同组件或祖先组件的 watch），
 * DbForm 内部子组件的 watch 晚于 DbForm 执行，取到的已是置位后的状态，这类场景不要改选项、直接跳转。
 * 跳转被取消（aborted）或失败时执行 rollback 把选项还原为当前页面，还原引起的置位同样复原；
 * 还原选项若再次触发跳转，目标是当前页面（duplicated），不会再回滚，避免来回切换
 */
export const switchSiblingRoute = (
  navigate: () => Promise<NavigationFailure | void | undefined>,
  rollback: () => void,
) => {
  const changeConfirmBeforeSwitch = window.changeConfirm;
  const restore = () => {
    rollback();
    nextTick(() => {
      window.changeConfirm = changeConfirmBeforeSwitch;
    });
  };
  return nextTick()
    .then(() => {
      window.changeConfirm = changeConfirmBeforeSwitch;
      return navigate();
    })
    .then((failure) => {
      if (isNavigationFailure(failure, NavigationFailureType.aborted)) {
        restore();
      }
    })
    .catch(restore);
};

export const leaveConfirm = (): Promise<boolean> => {
  if (!window.changeConfirm || window.changeConfirm === 'popover') {
    return Promise.resolve(true);
  }

  return openLeaveConfirmBox().then((isConfirm) => {
    if (!isConfirm) {
      return Promise.reject(false);
    }
    window.changeConfirm = false;
    return true;
  });
};
