import { h } from 'vue';

export default {
  name: 'render-list',
  props: {
    selector: {
      type: Object,
    },
    user: {
      type: Object,
    },
    keyword: {
      type: String,
    },
    index: {
      type: Number,
    },
    disabled: {
      type: Boolean,
    },
  },
  setup(props: any): any {
    return () => props.selector.renderList(h, {
      user: props.user,
      index: props.index,
      keyword: props.keyword,
      disabled: props.disabled,
    });
  },
};
