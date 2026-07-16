import { type ComponentInternalInstance, getCurrentInstance, type Ref } from 'vue';

export const useTableExpose = <T>(tableRef: Ref<null | T>) => {
  const instance = getCurrentInstance() as {
    exposeProxy: Partial<T>;
  } & ComponentInternalInstance;
  const proxy = new Proxy(
    {},
    {
      get(_, prop) {
        return Reflect.get(tableRef.value || {}, prop);
      },
    },
  );
  instance.exposeProxy = proxy;
};
