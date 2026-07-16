/* eslint-disable @typescript-eslint/no-explicit-any */
/*
 * Tencent is pleased to support the open source community by making
 * 蓝鲸智云PaaS平台 (BlueKing PaaS) available.
 *
 * Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
 *
 * 蓝鲸智云PaaS平台 (BlueKing PaaS) is licensed under the MIT License.
 *
 * License for 蓝鲸智云PaaS平台 (BlueKing PaaS):
 *
 * ---------------------------------------------------
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
 * to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
 * the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
 * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
export const camelCase = (str: string) => {
  if (typeof str !== 'string') return str;
  return str.replace(/-([a-z])/g, (_, n) => n.toUpperCase());
};

export const camelCaseObject = <T extends Record<string, any>>(obj: T) => {
  if (!obj) return {};
  return Object.entries(obj).reduce((acc, [key, value]) => {
    acc[camelCase(key)] = value;
    return acc;
  }, {}) as T;
};

export const camelCaseArray = <T extends Record<string, any>>(arr: T[]) => {
  if (!Array.isArray(arr)) return arr;
  return arr.map(camelCaseObject);
};

export const deleteUndefinedProps = <T extends Record<string, any>>(obj: T) => {
  if (!obj) return obj;
  return Object.entries(obj).reduce((acc, [key, value]) => {
    if (value !== undefined) {
      acc[key] = value;
    }
    return acc;
  }, {}) as T;
};

export const makeMap = (list: Array<number | string> = []): Record<number | string, boolean> => {
  const map = Object.create(null);
  list.forEach(item => {
    map[item] = true;
  });
  return map;
};
