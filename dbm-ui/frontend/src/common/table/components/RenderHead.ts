import _ from 'lodash';
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'RenderHead',
  props: {
    column: {
      type: Object,
      required: true,
    },
    index: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    if (_.isFunction(props.column.renderHead)) {
      return () =>
        props.column.renderHead({
          column: props.column,
          index: props.index,
        });
    }

    if (_.isFunction(props.column.label)) {
      return () =>
        props.column.label({
          column: props.column,
          index: props.index,
        });
    }

    return () => null;
  },
});
