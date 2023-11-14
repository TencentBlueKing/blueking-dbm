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

import {
  reactive,
  toRefs,
} from 'vue';

export type Rules = Array<{
  validator: (value: any) => boolean | Promise<boolean>,
  message: string | (() => string)
}>

const getRuleMessage = (rule: Rules[0]) => {
  if (typeof rule.message === 'function') {
    return rule.message();
  }
  return rule.message;
};

export default function (rules: Rules|undefined) {
  const state = reactive({
    loading: false,
    error: false,
    message: '',
  });

  const validator = (targetValue: any) => {
    state.error = false,
    state.message = '';
    if (!rules) {
      return Promise.resolve(true);
    }
    const run = (() => {
      let stepIndex = -1;
      return (): Promise<boolean> => {
        stepIndex = stepIndex + 1;
        if (stepIndex >= rules.length) {
          return Promise.resolve(true);
        }
        const rule = rules[stepIndex];
        return Promise.resolve()
          .then(() => {
            const result = rule.validator(targetValue);
            // 异步验证
            if (typeof result !== 'boolean'
                && typeof result.then === 'function') {
              return result.then((data: boolean) => {
              // 异步验证结果为 false
                if (data === false) {
                  return Promise.reject(getRuleMessage(rule));
                }
              }).then(() => run(), () => {
                state.error = true;
                const message = getRuleMessage(rule);
                state.message = message;
                return Promise.reject(message);
              });
            }
            // 验证失败
            if (!result) {
              state.error = true;
              const message = getRuleMessage(rule);
              state.message = message;
              return Promise.reject(message);
            }
            // 下一步
            return run();
          });
      };
    })();

    return run();
  };

  return {
    ...toRefs(state),
    validator,
  };
}
