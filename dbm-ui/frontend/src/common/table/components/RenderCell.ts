import { defineComponent } from 'vue';

export default defineComponent({
  name: 'RenderCell',
  props: {
    column: {
      type: Object,
      required: true,
    },
    params: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    return () =>
      props.column.slots.default({
        cell: props.column.field ? props.params.row[props.column.field] : '',
        data: props.params.row,
        column: props.column,
        index: props.params.$columnIndex,
        row: props.params.row,
        rows: props.params.data,
      });
  },
});
