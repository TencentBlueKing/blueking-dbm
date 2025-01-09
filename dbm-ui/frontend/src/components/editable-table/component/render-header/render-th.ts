import { defineComponent, h, resolveDirective, withDirectives } from 'vue';

import type { IContext as IColumnContext } from '../../Column.vue';

export default defineComponent({
  name: 'RenderColumnHead',
  props: {
    column: {
      type: Object as () => IColumnContext,
      required: true,
    },
    columnSizeConfig: {
      type: Object as () => Record<string, { renderWidth: number }>,
      required: true,
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
                props.columnSizeConfig[props.column.key].renderWidth > 0
                  ? `${props.columnSizeConfig[props.column.key].renderWidth - 20}px`
                  : '',
            },
          },
          childNode,
        ),
      );
    };
  },
});
