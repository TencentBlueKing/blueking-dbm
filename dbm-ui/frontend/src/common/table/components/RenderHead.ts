import { defineComponent } from 'vue';

export default defineComponent({
  name: 'RenderHead',
  props: {
    column: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    return () =>
      props.column.slots.header({
        column: props.column,
      });
  },
});
