import { computed, inject, type InjectionKey, provide, type Ref } from 'vue';

import type { IRegisteredColumnProps } from '../types/table';

export type ProvideTableFuncs = {
  addColumnProps: (id: string, columnProps: Ref<IRegisteredColumnProps>) => void;
  deleteColumn: (id: string) => void;
};
const TABLE_COLUMN_KEY: InjectionKey<ProvideTableFuncs> = Symbol('table-column-key');

export const useTableInject = () => computed(() => inject(TABLE_COLUMN_KEY));

export const useTableProvide = (data: ProvideTableFuncs) => {
  provide(TABLE_COLUMN_KEY, data);
};
