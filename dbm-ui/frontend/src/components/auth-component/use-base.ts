import {
  computed,
  onMounted,
} from 'vue';
import { useRequest } from 'vue-request';

import { checkAuthAllowed } from '@services/source/iam';

import { permissionDialog } from '@utils';

export interface Props {
  permission?: string | boolean,
  actionId: string,
  resource?: string | number,
}

export default function (props: Props) {
  const {
    data: checkResultMap,
    loading,
    run,
  } = useRequest(checkAuthAllowed, {
    manual: true,
  });

  const isShowRaw = computed(() => {
    console.log('checkResultMap = ', checkResultMap);
    if (props.permission === true) {
      return true;
    }
    return false;
    // return Boolean(checkResultMap.value[props.actionId]);
  });

  // 检测权限
  const checkPermission = () => {
    if (!props.actionId) {
      return;
    }

    run({
      action_ids: [props.actionId],
      resources: [
        {
          type: 'mysql',
          id: props.resource,
        },
      ],
    });
  };

  // watch(() => props.resource, (resource) => {
  //   if (resource) {
  //     // 资源信息变化需要重新鉴权
  //     checkPermission();
  //   }
  // });


  const handleRequestPermission = (event: Event) => {
    if (loading.value) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    permissionDialog(undefined, {
      action_ids: props.actionId,
      resources: props.resource,
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
