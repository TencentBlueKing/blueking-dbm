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

import { t } from '@locales/index';

import { messageError, messageSuccess, messageWarn } from './message';

// 浏览器拒绝复制时可能返回 false，也可能直接抛错，统一成布尔值
const copyText = (value: string) => {
  // 记下复制前的焦点，复制完还回去，避免焦点丢失影响弹层、终端的键盘操作
  const prevActiveElement = document.activeElement;
  const textarea = document.createElement('textarea');
  textarea.value = value;
  // 固定定位并置于底层，避免页面滚动和闪现
  textarea.style.position = 'fixed';
  textarea.style.top = '0';
  textarea.style.zIndex = '-99999';
  document.body.appendChild(textarea);

  try {
    textarea.focus({ preventScroll: true });
    textarea.select();
    return document.execCommand('copy');
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
    if (prevActiveElement instanceof HTMLElement) {
      prevActiveElement.focus({ preventScroll: true });
    }
  }
};

/**
 * 复制文本到剪贴板，并提示复制结果
 * @param value 复制内容，为空时提示没有可复制数据
 * @param message 复制成功的提示文案
 */
export const execCopy = (value: string, message = t('复制成功')) => {
  if (!value) {
    messageWarn(t('没有可复制数据'));
    return;
  }
  if (copyText(value)) {
    messageSuccess(message);
    return;
  }
  messageError(t('复制失败'));
};
