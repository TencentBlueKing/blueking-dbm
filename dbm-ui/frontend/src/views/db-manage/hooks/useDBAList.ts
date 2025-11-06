import type { Ref } from 'vue';
import { useRequest } from 'vue-request';

import { getAdmins } from '@services/source/dbadmin';

import { useSystemEnviron } from '@stores';

import { DBTypes } from '@common/const';

export default (dbType: Ref<DBTypes | undefined>) => {
  const { urls } = useSystemEnviron();
  const { data: dbaList } = useRequest(getAdmins, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

  return computed(() => {
    if (!dbType.value) {
      return [];
    }
    if (urls.DBA_ROBOT?.[dbType.value]) {
      return [urls.DBA_ROBOT[dbType.value]];
    }
    return dbaList.value?.find((item) => item.db_type === dbType.value)?.users || [];
  });
};
