import { useRequest } from 'vue-request';

import { queryClusterInstanceCount } from '@services/source/dbbase';

export default () => {
  const { data, loading } = useRequest(queryClusterInstanceCount, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

  return {
    data,
    loading,
  };
};
