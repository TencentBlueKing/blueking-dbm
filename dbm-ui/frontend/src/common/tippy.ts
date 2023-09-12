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

import tippy, {
  type Instance,
  type MultipleTargets,
  type Props,
  type SingleTarget } from 'tippy.js';

const dbTheme = 'db-tippy';
const dbDefaultProps = { theme: dbTheme };

/**
 * tippy
 */
export function dbTippy (targets: MultipleTargets, optionalProps?: Partial<Props>): Instance[]
export function dbTippy (targets: SingleTarget, optionalProps?: Partial<Props>): Instance
export function dbTippy(targets: MultipleTargets | SingleTarget, optionalProps?: Partial<Props>) {
  const props = optionalProps ? { ...optionalProps } : optionalProps;
  // 添加 db-tippy 作用域
  if (props) {
    const { theme } = props;
    props.theme = theme ? `${dbTheme} ${props.theme}` : dbTheme;
  }
  if (targets instanceof Element) {
    const target = targets;
    return tippy(target, props || dbDefaultProps);
  }
  return tippy(targets, props || dbDefaultProps);
}
