import { useRequest } from 'vue-request';

import { queryClusterInstanceCount } from '@services/source/dbbase';

export default () => {
  const { loading, data } = useRequest(queryClusterInstanceCount, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

  return {
    loading,
    data,
  };
};
