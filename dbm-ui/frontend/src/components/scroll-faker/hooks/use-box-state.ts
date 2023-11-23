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
  type ComponentInternalInstance,
  getCurrentInstance,
  reactive,
} from 'vue';

import type { IContext } from '../index.vue';

export default function () {
  const { proxy } = getCurrentInstance() as ComponentInternalInstance & {proxy: IContext};

  const state = reactive({
    contentScrollHeight: 0,
    contentScrollWidth: 0,
    isRenderVerticalScroll: false,
    isRenderHorizontalScrollbar: false,
    styles: {
      width: '',
      height: '',
    },
  });


  const initState = () => {
    if (proxy.$refs.scrollBox && proxy.$refs.scrollContent) {
      const {
        scrollHeight,
        scrollWidth,
      } = proxy.$refs.scrollContent as Element;
      state.contentScrollHeight = scrollHeight;
      state.contentScrollWidth = scrollWidth;

      const {
        width: boxWidth,
        height: boxHeight,
      } = proxy.$refs.scrollBox.getBoundingClientRect();
        // 内容区高度大于容器高度显示垂直滚动条
      state.isRenderVerticalScroll = Math.ceil(state.contentScrollHeight) > Math.ceil(boxHeight);
      // 内容区宽度大于容器宽度显示水平滚动条
      state.isRenderHorizontalScrollbar = Math.ceil(state.contentScrollWidth) > Math.ceil(boxWidth);
      const styles = {
        width: '100%',
        height: '100%',
        maxHeight: '',
        maxWidth: '',
      };
        // 计算滚动容器的展示宽高
      const {
        height: scrollBoxStyleHeight,
        maxHeight: scrollBoxStyleMaxHeight,
        width: scrollBoxStyleWidth,
        maxWidth: scrollBoxStyleMaxWidth,
      } = proxy.$refs.scrollBox.style;
      if (state.isRenderVerticalScroll) {
        if (scrollBoxStyleHeight) {
          styles.height = scrollBoxStyleHeight;
        } else if (scrollBoxStyleMaxHeight) {
          styles.maxHeight = scrollBoxStyleMaxHeight;
        }
      }
      if (state.isRenderHorizontalScrollbar) {
        if (scrollBoxStyleWidth) {
          styles.width = scrollBoxStyleWidth;
        } else if (scrollBoxStyleMaxWidth) {
          styles.maxWidth = scrollBoxStyleMaxWidth;
        }
      }

      state.styles = Object.freeze(styles);
    }
  };

  return {
    state,
    initState,
  };
}
