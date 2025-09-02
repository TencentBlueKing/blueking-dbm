import _ from 'lodash';
import { computed, shallowRef } from 'vue';

import type { Props as ContextProps } from '@components/db-quick-serach/bk-quick-search/Index.vue';

export default <T extends { label: string; value: string | number }>(config: ContextProps['data'][number]) => {
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
        remoteList.value = data as T[];
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
