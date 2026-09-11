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

import { Checkbox, type CheckboxProps } from 'tdesign-vue-next';
import { defineComponent, h } from 'vue';

/**
 * tdesign Checkbox 只在 setup 阶段读一次 props.onChange 并固化进闭包。
 * 表格 data 更新时组件实例是复用（patch）而非重建，setup 不再执行，
 * 单元格里触发的仍是首次渲染的回调，闭包捕获的 row 已经过期。
 * 这里向内层传入稳定的 handler，触发时才去取调用方最新的 onChange。
 */
export default defineComponent<CheckboxProps>({
  name: 'TdCheckbox',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    const handleChange: CheckboxProps['onChange'] = (checked, context) => {
      (attrs.onChange as CheckboxProps['onChange'])?.(checked, context);
    };

    return () => h(Checkbox, { ...attrs, onChange: handleChange }, slots);
  },
});
