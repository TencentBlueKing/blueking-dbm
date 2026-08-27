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

import { defineComponent, h, resolveDirective, withDirectives } from 'vue';

import type { IContext as IColumnContext } from '../../Column.vue';

export default defineComponent({
  name: 'RenderColumnHead',
  props: {
    column: {
      required: true,
      type: Object as () => IColumnContext,
    },
    columnSizeConfig: {
      required: true,
      type: Object as () => Record<string, { renderWidth: number }>,
    },
  },
  setup(props) {
    return () => {
      const childNode = [
        withDirectives(
          h(
            'div',
            {
              class: {
                'bk-editable-table-th-text': true,
                'bk-editable-table-th-text-description': Boolean(props.column.props.description),
              },
            },
            props.column.slots.head ? props.column.slots.head() : props.column.props.label || '',
          ),
          [
            [
              resolveDirective('bk-tooltips'),
              {
                content: props.column.props.description || '',
                disabled: !props.column.props.description,
              },
            ],
          ],
        ),
      ];

      if (!props.column.slots.head && props.column.slots.headPrepend) {
        childNode.unshift(
          h(
            'div',
            {
              class: 'bk-editable-table-th-prepend',
            },
            props.column.slots.headPrepend(),
          ),
        );
      }

      if (!props.column.slots.head && props.column.slots.headAppend) {
        childNode.push(
          h(
            'div',
            {
              class: 'bk-editable-table-th-append',
            },
            props.column.slots.headAppend(),
          ),
        );
      }
      return h(
        'th',
        {
          class: {
            'bk-editable-table-header-column': true,
            'is-required': props.column.props.required,
          },
          'data-name': props.column.key,
        },
        h(
          'div',
          {
            class: 'bk-editable-table-label-cell',
            style: {
              width:
                props.columnSizeConfig[props.column.key]!.renderWidth > 0
                  ? `${props.columnSizeConfig[props.column.key]!.renderWidth - 20}px`
                  : '',
            },
          },
          childNode,
        ),
      );
    };
  },
});
