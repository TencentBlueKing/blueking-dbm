import {
  defineComponent,
  useSlots,
} from 'vue';

import('./component.css');

export default defineComponent({
  setup() {
    const slots = useSlots();
    return () => (
      <div>{slots.default?.()}</div>
    );
  },
});
