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
      props.column.render({
        cell: props.column.field ? props.params.row[props.column.field] : '',
        data: props.params.row,
        column: props.params.column,
        index: props.params.$rowIndex,
        rows: props.params.data,
      });
  },
});
