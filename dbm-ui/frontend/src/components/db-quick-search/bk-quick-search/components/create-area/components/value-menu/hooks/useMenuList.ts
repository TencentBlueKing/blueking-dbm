import _ from 'lodash';

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
      // 请求失败时清空候选，避免继续展示上一次关键字的结果，也避免未处理的 Promise 拒绝
      .catch(() => {
        if (currentRequestId === latestRequestId) {
          remoteList.value = [];
        }
      })
      .finally(() => {
        if (currentRequestId === latestRequestId) {
          isLoading.value = false;
        }
      });
  };

  const debounceFetchRemoteList = _.debounce(() => {
    if (config.remoteMethod && config.remoteSearch) {
      fetchRemoteList();
    }
  }, 300);

  watch(filterKey, debounceFetchRemoteList);

  // 面板关闭后不再发出还在防抖中的请求
  onBeforeUnmount(() => {
    debounceFetchRemoteList.cancel();
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
