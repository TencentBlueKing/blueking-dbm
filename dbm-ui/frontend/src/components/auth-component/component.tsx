import { defineComponent } from 'vue';

import { attrsWithoutListener } from '@utils';

import useBase from './use-base';

import('./component.css');

export default defineComponent({
  inheritAttrs: false,
  props: {
    permission: {
      type: [String, Boolean],
      default: 'normal',
    },
    actionId: {
      type: String,
      default: '',
    },
    resource: {
      type: [String, Number],
      default: '',
    },
    bizId: {
      type: [String, Number],
    },
  },
  setup(props) {
    const { loading, isShowRaw, handleRequestPermission } = useBase(props);

    return {
      loading,
      isShowRaw,
      handleRequestPermission,
    };
  },
  render() {
    if (this.isShowRaw) {
      return <span {...this.$attrs}>{this.$slots.default?.()}</span>;
    }

    const inheritAttrs = attrsWithoutListener(this.$attrs);

    return (
      <div
        {...inheritAttrs}
        class='permission-disable-component'>
        {this.$slots.default?.()}
        <div
          class='permission-disable-mask'
          v-cursor
          onClick={this.handleRequestPermission}
        />
      </div>
    );
  },
});
