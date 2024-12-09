import { inject } from 'vue';

import { EditableTableColumnKey } from './Column.vue';
import { type IRule } from './types';

export default (
  options = {} as {
    rules?: IRule[];
  },
) => {
  const columnContext = inject(EditableTableColumnKey);

  // if (!columnContext) {
  //   throw new Error('not found EditColumn');
  // }

  if (columnContext && options.rules) {
    columnContext.registerRules(options.rules);
  }

  return columnContext;
};
