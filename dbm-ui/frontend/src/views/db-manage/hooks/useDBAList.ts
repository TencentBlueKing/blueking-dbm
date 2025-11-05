import type { Ref } from 'vue';
import { useRequest } from 'vue-request';

import { getAdmins } from '@services/source/dbadmin';

import { DBTypes } from '@common/const';

export default (dbType: Ref<DBTypes | undefined>) => {
  const { data: dbaList } = useRequest(getAdmins, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

  return computed(() => {
    return dbaList.value?.find((item) => item.db_type === dbType.value)?.users || [];
  });
};
