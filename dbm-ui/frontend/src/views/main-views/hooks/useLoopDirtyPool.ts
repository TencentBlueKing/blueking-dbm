import { useRequest } from 'vue-request';

import {
  getDirtyMachines,
} from '@services/dbResource';

export const useLoopDirtyPool = () => {
  const {
    data,
  } = useRequest(getDirtyMachines, {
    defaultParams: [{
      limit: 1,
      offset: 0,
    }, {
      globalError: false,
    }],
    pollingInterval: 10000,
  });

  return computed(() => data.value?.count ?? 0);
};
