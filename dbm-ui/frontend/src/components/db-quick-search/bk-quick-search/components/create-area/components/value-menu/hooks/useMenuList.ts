import _ from 'lodash';
import { computed, shallowRef } from 'vue';

import type { Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

import { splitSearchKeyword } from '../common/searchKeyword';

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

  // 请求序号，只接受最后一次请求的结果，避免先发的慢响应覆盖后发的结果
  let latestRequestId = 0;
  const fetchRemoteList = () => {
    if (!isRemoteList.value) {
      return;
    }

    latestRequestId = latestRequestId + 1;
    const currentRequestId = latestRequestId;

    isLoading.value = true;
    Promise.resolve()
      .then(() =>
        config!.remoteMethod!({
          keyword: splitSearchKeyword(filterKey.value).join(','),
        }),
      )
      .then((data) => {
        if (currentRequestId !== latestRequestId) {
          return;
        }
        remoteList.value = data as T[];
      })
      .finally(() => {
        if (currentRequestId === latestRequestId) {
          isLoading.value = false;
        }
      });
  };

  watch(
    filterKey,
    _.debounce(() => {
      if (config.remoteMethod && config.remoteSearch) {
        fetchRemoteList();
      }
    }, 300),
  );

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
