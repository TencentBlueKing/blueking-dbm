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

import _ from 'lodash';

import RedisModel from '@services/model/redis/redis';

import { TicketTypes } from '@common/const';

import { messageWarn } from '@utils';

import { t } from '@locales/index';

export const useShowDeleteKeys = () => {
  const state = reactive({
    isShow: false,
    data: [] as RedisModel[],
  });

  const handleShow = (data: RedisModel[]) => {
    if (
      data.some(
        (item) =>
          item.operations.length > 0 &&
          item.operations.map((op) => op.ticket_type).includes(TicketTypes.REDIS_INSTANCE_DESTROY),
      )
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    if (data.some((item) => item.bk_cloud_id > 0)) {
      messageWarn(t('暂不支持跨管控区域删除Key'));
      return;
    }
    state.isShow = true;
    state.data = _.cloneDeep(data);
  };

  return {
    state,
    handleShow,
  };
};
