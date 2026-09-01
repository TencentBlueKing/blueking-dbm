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

import _ from 'lodash';

export interface IRowspanTask {
  getRowIndex: () => number;
  run: (rowspanNumMap: Map<string, number>) => void;
}

export default function () {
  const taskList: IRowspanTask[] = [];

  const pushRowspanTask = (task: IRowspanTask) => {
    taskList.push(task);
  };

  const removeRowspanTask = (run: IRowspanTask['run']) => {
    _.remove(taskList, (item) => item.run === run);
  };

  // 按行序重新计算所有单元格的合并状态
  // 合并计数每一趟独立，不受上一趟计算残留的影响
  const runRowspanTask = () => {
    const rowspanNumMap = new Map<string, number>();
    _.sortBy(taskList, (item) => item.getRowIndex()).forEach((item) => item.run(rowspanNumMap));
  };

  return {
    pushRowspanTask,
    removeRowspanTask,
    runRowspanTask,
  };
}
