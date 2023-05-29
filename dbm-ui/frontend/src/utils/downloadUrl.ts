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

export const downloadUrl = (url: string) => {
  // 创建隐藏的可下载链接

  const eleLink = document.createElement('a');
  eleLink.style.display = 'none';
  eleLink.href = url;

  // 触发点击
  document.body.appendChild(eleLink);
  const { changeConfirm } = window;
  window.changeConfirm = false;
  eleLink.click();
  setTimeout(() => {
    window.changeConfirm = changeConfirm;
  });

  // 然后移除
  document.body.removeChild(eleLink);
};
