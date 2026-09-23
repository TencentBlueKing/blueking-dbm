import type { PropType } from 'vue';

import type { Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export default defineComponent({
  props: {
    config: {
      required: true,
      type: Object as PropType<ContextProps['data'][number]>,
    },
    modelValue: {
      required: true,
      type: String,
    },
    remoteSearch: {
      required: true,
      type: Boolean,
    },
  },

  emits: ['change'],
  setup(props, context) {
    return () => {
      return h(props.config.component!, {
        onChange: (value: unknown) => {
          context.emit('change', value);
        },
        remoteSearch: props.remoteSearch,
        ...(props.config.props || { not: 'empty' }),
        modelValue: props.modelValue,
      });
    };
  },
});
