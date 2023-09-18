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

import { Button, Dialog } from 'bkui-vue';
import _ from 'lodash';
import { type ComponentInternalInstance, defineComponent, isVNode, type PropType } from 'vue';

import { t } from '@locales/index';

export interface InfoOptions {
  width?: number | string,
  extCls?: string
  confirmTxt?: string
  confirmTheme?: InstanceType<typeof Button>['$props']['theme']
  cancelTxt?: string
  title?: ComponentInternalInstance | (() => JSX.Element) | string
  footer?: null | (() => JSX.Element)
  content?: ComponentInternalInstance | (() => JSX.Element) | string
  onConfirm?: () => boolean | Promise<boolean>
  onCancel?: () => void
  props?: {
    [propName: string]: any
  }
}

const info = defineComponent({
  props: {
    options: {
      type: Object as PropType<InfoOptions>,
      default: () => ({}),
    },
  },
  setup(props) {
    const instance = getCurrentInstance();
    const state = reactive({
      visible: false,
      loading: false,
      options: props.options,
    });

    const methods = {
      service: (options: object) => {
        state.loading = false;
        state.options = options;
        methods.show();
      },
      show: () => (state.visible = true),
      hide: () => (state.visible = false),
    };

    const handler = {
      onConfirm: async () => {
        state.loading = true;
        const result = await state.options.onConfirm?.();
        state.loading = false;
        result && methods.hide();
      },
      onCancel: () => {
        state.options.onCancel?.();
        methods.hide();
      },
    };

    instance && instance.proxy && Object.assign(instance.proxy, methods);

    const title = computed(() => {
      if (isVNode(state.options.title)) {
        return <title />;
      }
      return _.isFunction(state.options.title) ? state.options.title() : state.options.title;
    });

    const content = computed(() => {
      if (isVNode(state.options.content)) {
        return <content />;
      }
      return _.isFunction(state.options.content) ? state.options.content() : state.options.content;
    });

    const footer = computed(() => {
      if (_.isFunction(state.options.footer)) {
        return state.options.footer();
      }
      const theme = state.options.confirmTheme || 'primary';
      return [
        <Button theme={theme} class="mr-8" loading={state.loading} onClick={handler.onConfirm}>{state.options.confirmTxt || t('确定')}</Button>,
        <Button onClick={handler.onCancel}>{state.options.cancelTxt || t('取消')}</Button>,
      ];
    });

    onMounted(() => {
      state.visible = true;
    });

    return () => (
      <Dialog
        v-model:is-show={state.visible}
        theme="primary"
        header-align="center"
        dialog-type="show"
        class={['db-info-dialog', state.options.extCls ?? '']}
        width={ state.options.width || 400}
        height="auto"
        quick-close={false}
        esc-close={false}
        onClosed={handler.onCancel}
        {...state.options.props}>
        {{
          header: () => (title.value),
          default: () => (
            <div class="db-info-dialog__main">
              <div class="db-info-dialog__content">
                {content.value}
              </div>
              <div class="db-info-dialog__footer">
                {footer.value}
              </div>
            </div>
          ),
        }}
      </Dialog>
    );
  },
});

export const useInfo = (() => {
  let instance: any;
  return (options: InfoOptions) => {
    if (instance) {
      instance.service(options);
      return instance;
    }
    const div = document.createElement('div');
    document.body.appendChild(div);
    const app = createApp(info, { options });
    instance = app.mount(div);
    return instance;
  };
})();
