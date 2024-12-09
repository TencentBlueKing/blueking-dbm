import { defineComponent, h } from 'vue';

import type { IContext as IColumnContext } from '../../Column.vue';

export default defineComponent({
  name: 'RenderColumnCell',
  props: {
    column: {
      type: Object as () => IColumnContext,
      required: true,
    },
  },
  setup(props) {
    return () =>
      h(
        'td',
        {
          class: 'bk-editable-table-body-column',
        },
        h(
          'div',
          {
            class: 'bk-editable-table-cell',
          },
          props.column.slots.default(),
        ),
      );
  },
});
