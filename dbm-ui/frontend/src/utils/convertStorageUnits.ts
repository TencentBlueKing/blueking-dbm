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

/**
 * 存储单位转换
 * @param value 待转换值
 * @param fromUnit 待转换单位
 * @param toUnit 目标单位
 * @returns {number} 转换结果
 */

const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'] as const;
type Unit = (typeof units)[number];

export const convertStorageUnits = (value: number, fromUnit: Unit, toUnit: Unit) => {
  const fromIndex = units.indexOf(fromUnit);
  const toIndex = units.indexOf(toUnit);

  if (fromIndex === -1 || toIndex === -1) {
    return 0;
  }

  const conversionFactor = 1024 ** (fromIndex - toIndex);

  return value * conversionFactor;
};
