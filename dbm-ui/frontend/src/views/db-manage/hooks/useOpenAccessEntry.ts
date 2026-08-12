import { useRoute } from 'vue-router';

import { simpleCheckAllowed } from '@services/source/iam';

import { messageWarn, permissionDialog } from '@utils';

import { t } from '@locales/index';

const OPEN_ACCESS_ENTRY_KEY = 'access_entry';

interface OpenAccessEntryParams<T> {
  /** 查看访问凭据的 action_id，必传，与各集群 AuthButton 保持一致 */
  actionId: string;
  /** 集群详情数据：从中取 id（resource_id）、isOffline、permission */
  data: T;
  /** 鉴权通过后打开「获取访问方式」弹窗 */
  onOpen: () => void;
}

/**
 * 判断当前是否通过「列表 url + clusterId + ?open=access_entry」直达打开「获取访问方式」，
 * 并提供与 AuthButton 一致的鉴权流程：有权限打开弹窗，无权限弹无权限申请弹窗，
 * 集群已禁用时以 messageWarn 提示且不打开弹窗。
 */
export default function useOpenAccessEntry() {
  const route = useRoute();

  const isOpenAccessEntry = computed(() => {
    if (route.query.open !== OPEN_ACCESS_ENTRY_KEY) {
      return false;
    }
    // clusterId 需存在且为有效数字，避免参数异常时误触发
    return Number(route.params.clusterId) > 0;
  });

  const handleOpenAccessEntry = <
    T extends { id: string | number; isOffline: boolean; permission?: Record<string, boolean | string> },
  >(
    params: OpenAccessEntryParams<T>,
  ) => {
    if (!isOpenAccessEntry.value) {
      return;
    }
    const { actionId, data, onOpen } = params;
    // 集群已禁用：不打开弹窗，messageWarn 提示
    if (data.isOffline) {
      messageWarn(t('集群已禁用，无法获取访问方式'));
      return;
    }
    const permission = data.permission?.[actionId];
    if (permission === true) {
      onOpen();
      return;
    }
    simpleCheckAllowed({
      action_id: actionId,
      resource_id: data.id,
    }).then((allowed) => {
      if (allowed) {
        onOpen();
      } else {
        permissionDialog(undefined, {
          action_id: actionId,
          resource_id: data.id,
        });
      }
    });
  };

  return {
    handleOpenAccessEntry,
    isOpenAccessEntry,
  };
}
