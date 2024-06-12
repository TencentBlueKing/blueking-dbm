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
 * 比较版本号大小
 * @param prevVersion 待比较版本号1
 * @param nextVersion 待比较版本号2
 * @returns {number} 比较结果，1：版本号1更大；-1：版本号2更大；0：版本号相同；
 */
export const compareVersions = (prevVersion: string, nextVersion: string) => {
  // 将版本号分割成数组
  const prevVersionList = prevVersion.split('.').map(Number);
  const nextVersionList = nextVersion.split('.').map(Number);

  // 获取最长的数组长度
  const maxLength = Math.max(prevVersionList.length, nextVersionList.length);

  // 补全版本号短的数组为相同长度，缺省部分视为 0
  while (prevVersionList.length < maxLength) {
    prevVersionList.push(0);
  }
  while (nextVersionList.length < maxLength) {
    nextVersionList.push(0);
  }

  // 逐个比较各部分版本号
  for (let i = 0; i < maxLength; i++) {
    if (prevVersionList[i] > nextVersionList[i]) {
      return 1;
    }
    if (prevVersionList[i] < nextVersionList[i]) {
      return -1;
    }
  }

  // 如果所有部分都相同，则版本号相等
  return 0;
};
