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

  let isRunPending = false;

  // 按行序重新计算所有单元格的合并状态
  // 合并计数每一趟独立，不受上一趟计算残留的影响
  // 延后到本轮渲染结束后执行，并把期间的多次触发合并成一次：每个单元格挂载、model 变化都会各自触发，
  // 逐次全量计算的开销随单元格数平方增长，上百行时会长时间占用主线程
  const runRowspanTask = () => {
    if (isRunPending) {
      return;
    }
    isRunPending = true;
    nextTick(() => {
      isRunPending = false;
      const rowspanNumMap = new Map<string, number>();
      _.sortBy(taskList, (item) => item.getRowIndex()).forEach((item) => item.run(rowspanNumMap));
    });
  };

  return {
    pushRowspanTask,
    removeRowspanTask,
    runRowspanTask,
  };
}
