import { defineComponent, h } from 'vue';

import type { IContext as IColumnContext } from '../../Column.vue';

export default defineComponent({
  name: 'RenderColumnCell',
  props: {
    column: {
      required: true,
      type: Object as () => IColumnContext,
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
