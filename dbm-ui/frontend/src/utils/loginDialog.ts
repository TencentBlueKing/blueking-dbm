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

let isShow = false;
export const loginDialog = (loginUrl: string) => {
  if (isShow) {
    return;
  }
  const $dialogEle = document.createElement('div');
  $dialogEle.style.position = 'fixed';
  $dialogEle.style.top = '0';
  $dialogEle.style.right = '0';
  $dialogEle.style.bottom = '0';
  $dialogEle.style.left = '0';
  $dialogEle.style.backgroundColor = 'rgba(0, 0, 0, .6)';
  $dialogEle.style.zIndex = '99999';
  $dialogEle.style.fontSize = '0';

  const $iframeEle = document.createElement('iframe');
  $iframeEle.src = loginUrl;
  $iframeEle.width = '400';
  $iframeEle.height = '400';

  $iframeEle.style.display = 'block';
  $iframeEle.style.margin = 'calc((100vh - 470px) / 2) auto';
  $iframeEle.style.backgroundColor = '#fff';
  $iframeEle.style.borderRadius = '8px';
  $iframeEle.style.border = 'none';
  $iframeEle.style.boxShadow = '0 2px 6px 0 rgba(0,0,0,.1)';
  $dialogEle.appendChild($iframeEle);
  document.body.appendChild($dialogEle);
  isShow = true;
};
