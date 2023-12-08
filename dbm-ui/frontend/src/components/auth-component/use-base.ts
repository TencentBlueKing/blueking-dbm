import {
  computed,
  onMounted,
} from 'vue';
import { useRequest } from 'vue-request';

import { simpleCheckAllowed } from '@services/source/iam';

import { permissionDialog } from '@utils';

export interface Props {
  permission?: string | boolean,
  actionId: string,
  resource?: string | number,
}

export default function (props: Props) {
  const {
    data: checkResult,
    loading,
    run,
  } = useRequest(simpleCheckAllowed, {
    manual: true,
  });

  const isShowRaw = computed(() => {
    if (props.permission === true) {
      return true;
    }
    return checkResult.value;
  });

  // 检测权限
  const checkPermission = () => {
    if (!props.actionId) {
      return;
    }

    run({
      action_id: props.actionId,
      resource_ids: props.resource ? [props.resource] : [],
    });
  };

  const handleRequestPermission = (event: Event) => {
    if (loading.value) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    permissionDialog(undefined, {
      action_id: props.actionId,
      resource_ids: props.resource ? [props.resource] : [],
    });
  };


  onMounted(() => {
  // 初始没有权限信息，需要主动鉴权一次
    if (props.permission === 'normal') {
      checkPermission();
    }
  });

  return {
    loading,
    isShowRaw,
    handleRequestPermission,
  };
}
