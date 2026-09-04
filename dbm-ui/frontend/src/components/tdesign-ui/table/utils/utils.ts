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
export const camelCase = (str: string) => {
  if (typeof str !== 'string') return str;
  return str.replace(/-([a-z])/g, (_, n) => n.toUpperCase());
};

export const camelCaseObject = <T extends Record<string, any>>(obj: T) => {
  if (!obj) return {};
  return Object.entries(obj).reduce<T>(
    (acc, [key, value]) => ({
      ...acc,
      [camelCase(key)]: value,
    }),
    {} as T,
  );
};

export const camelCaseArray = <T extends Record<string, any>>(arr: T[]) => {
  if (!Array.isArray(arr)) return arr;
  return arr.map(camelCaseObject);
};

export const deleteUndefinedProps = <T extends Record<string, any>>(obj: T) => {
  if (!obj) return obj;
  return Object.entries(obj).reduce<T>(
    (acc, [key, value]) =>
      value === undefined
        ? acc
        : {
            ...acc,
            [key]: value,
          },
    {} as T,
  );
};

export const makeMap = (list: Array<number | string> = []): Record<number | string, boolean> => {
  const map = Object.create(null);
  list.forEach((item) => {
    map[item] = true;
  });
  return map;
};
