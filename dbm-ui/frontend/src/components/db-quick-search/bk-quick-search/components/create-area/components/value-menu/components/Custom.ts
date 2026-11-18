import type { PropType } from 'vue';

import type { IValue, Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export default defineComponent({
  props: {
    config: {
      required: true,
      type: Object as PropType<ContextProps['data'][number]>,
    },
    // 值面板传入的是已选值列表；新建条件时为空
    modelValue: {
      default: undefined,
      type: Array as PropType<IValue['values']>,
    },
    remoteSearch: {
      default: false,
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
