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

import { Radio, type RadioProps } from 'tdesign-vue-next';
import { defineComponent, h } from 'vue';

/**
 * 与 @components/tdesign-ui/checkbox 同因：tdesign Radio 也只在 setup 阶段读一次 props.onChange，
 * 实例复用时触发的仍是首次渲染的回调，闭包捕获的 row 已经过期。
 */
export default defineComponent<RadioProps>({
  name: 'TdRadio',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    const handleChange: RadioProps['onChange'] = (checked, context) => {
      (attrs.onChange as RadioProps['onChange'])?.(checked, context);
    };

    return () => h(Radio, { ...attrs, onChange: handleChange }, slots);
  },
});
