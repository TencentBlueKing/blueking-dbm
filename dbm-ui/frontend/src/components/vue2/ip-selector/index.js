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
  h,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';

import {
  Component,
  merge,
  Vue2,
} from '@blueking/ip-selector/dist/vue2.6.x.esm';

export default function (options) {
  merge(options);

  return {
    name: 'bk-ip-selector',
    props: Object.assign({}, Component.props),
    emits: [...Component.emits],
    setup(props, context) {
      const rootRef = ref();

      let app = new Vue2(Component);

      const syncProps = () => {
        Object.keys(props).forEach((propName) => {
          const newValue = props[propName];
          if (Object.prototype.toString.call(newValue) === '[object Object]') {
            const v = Object.keys(newValue).reduce((result, item) => ({
              ...result,
              [item]: newValue[item],
            }), {});
            // eslint-disable-next-line no-underscore-dangle
            app._props[propName] = Object.freeze(v);
          } else if (Object.prototype.toString.call(newValue) === '[object Array]') {
            // eslint-disable-next-line no-underscore-dangle
            app._props[propName] = [...newValue];
          } else {
            // eslint-disable-next-line no-underscore-dangle
            app._props[propName] = newValue;
          }
        });
      };

      const propWatchStack = [];
      Object.keys(props).forEach((propName) => {
        const unwatch = watch(() => props[propName], () => {
          syncProps();
        }, {
          immediate: true,
        });
        propWatchStack.push(unwatch);
      });

      Component.emits.forEach((eventName) => {
        app.$on(eventName, (...agrs) => {
          context.emit(eventName, ...agrs);
        });
      });
      syncProps();

      onMounted(() => {
        app.$mount();
        rootRef.value.appendChild(app.$el);
      });

      onBeforeUnmount(() => {
        propWatchStack.forEach(unwatch => unwatch());
        app.$el.parentNode.removeChild(app.$el);
        app.$destroy();
        app = null;
      });
      return {
        rootRef,
        app,
        propWatchStack,
      };
    },
    render() {
      return h('div', {
        role: 'bk-ip-selector',
        ref: 'rootRef',
      });
    },
  };
}
