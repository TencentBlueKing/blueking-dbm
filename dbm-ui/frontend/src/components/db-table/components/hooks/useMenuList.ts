import _ from 'lodash';
import { computed, shallowRef } from 'vue';

export default <T extends Record<string, any>>(config: {
  list?: T[];
  remoteMethod?: (params: {
    defaultValue?: string;
    keyword?: string;
  }) => Promise<{ label: string; value: number | string }[]>;
  remoteSearch?: boolean;
}) => {
  const filterKey = ref('');
  const remoteList = shallowRef<T[]>([]);
  const isLoading = ref(false);

  const isRemoteList = computed(() => _.isFunction(config.remoteMethod));

  const list = computed(() => {
    if (isRemoteList.value) {
      return remoteList.value;
    }

    return (config.list || []) as T[];
  });

  const fetchRemoteList = () => {
    if (!isRemoteList.value) {
      return;
    }

    isLoading.value = true;
    Promise.resolve()
      .then(() =>
        config!.remoteMethod!({
          keyword: filterKey.value,
        }),
      )
      .then((data) => {
        remoteList.value = data as unknown as T[];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  watch(filterKey, () => {
    if (config.remoteMethod && config.remoteSearch) {
      fetchRemoteList();
      return;
    }
  });

  fetchRemoteList();

  return {
    fetchRemoteList,
    filterKey,
    isRemoteList,
    list,
    loading: isLoading,
    remoteList,
  };
};
