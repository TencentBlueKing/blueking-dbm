import { h, inject } from 'vue';

export default {
  name: 'render-tag',
  props: ['username', 'user', 'index'],
  setup(props: any) {
    const parentSelector = inject('parentSelector');
    return () => (parentSelector as any).renderTag(h, {
      username: props.username,
      index: props.index,
      user: props.user,
    });
  },
};
