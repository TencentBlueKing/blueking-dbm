import type { Ref } from 'vue';
import { useRequest } from 'vue-request';

import { getAdmins } from '@services/source/dbadmin';

import { useSystemEnviron } from '@stores';

import { DBTypes } from '@common/const';

export default (
  dbType: Ref<DBTypes | undefined>,
  props: {
    bizId: number;
  },
) => {
  const { urls } = useSystemEnviron();
  const { data, run } = useRequest(getAdmins, {
    manual: true,
  });

  watch(dbType, () => {
    if (dbType.value) {
      run({
        db_type: dbType.value,
      });
    }
  });

  return computed(() => {
    if (!dbType.value) {
      return [];
    }
    if (urls.DBA_ROBOT?.[dbType.value]) {
      return [urls.DBA_ROBOT[dbType.value]];
    }
    if (props.bizId > 0) {
      const bizUserItem = data?.value?.data.find((item) => item.bk_biz_id === props.bizId)?.users;
      if (bizUserItem) {
        return bizUserItem;
      } else {
        return data?.value?.data.find((item) => item.bk_biz_id === 0)?.users || [];
      }
    } else {
      return data?.value?.data.find((item) => item.bk_biz_id === 0)?.users || [];
    }
  });
};
