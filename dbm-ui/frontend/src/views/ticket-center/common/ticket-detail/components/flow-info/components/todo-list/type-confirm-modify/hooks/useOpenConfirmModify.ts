/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import { useI18n } from 'vue-i18n';

import { OPEN_CONFIRM_MODIFY } from '@views/ticket-center/common/ticket-modify/constants';

import { messageWarn } from '@utils';

/**
 * 待我处理「待确认修改」的行内操作经 ticketDetail?open=confirm_modify 直达。
 * 确认步骤挂载时按是否可操作调用：可操作则自动打开确认抽屉，否则提示；
 * 单据已不在待确认修改时确认步骤不会挂载，由确认待办入口以不可操作调用，只提示。
 * 处理后去掉 open 参数，流程轮询导致组件重建时不会再次触发
 */
export default function useOpenConfirmModify() {
  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const handleOpenConfirmModify = (isAvailable: boolean, onOpen?: () => void) => {
    if (route.query.open !== OPEN_CONFIRM_MODIFY) {
      return;
    }
    router.replace({
      query: {
        ...route.query,
        open: undefined,
      },
    });
    if (!isAvailable) {
      messageWarn(t('当前没有需要您确认的修改'));
      return;
    }
    onOpen?.();
  };

  return {
    handleOpenConfirmModify,
  };
}
