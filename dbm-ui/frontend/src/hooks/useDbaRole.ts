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
import { useRequest } from 'vue-request';

import { checkBizDba, getUserDbaComponents } from '@services/source/dbadmin';

/**
 * 精确查询当前用户是否为指定业务+组件的 DBA
 * 用于业务空间下的功能权限控制
 */
export const useBizComponentDba = (bizId: number, dbType: string) => {
  const isDba = ref(false);

  const { loading } = useRequest(checkBizDba, {
    cacheKey: `dbaComponent_${bizId}_${dbType}`,
    defaultParams: [
      {
        bk_biz_id: bizId,
        db_type: dbType,
      },
    ],
    onSuccess(result) {
      isDba.value = result.is_biz_dba;
    },
  });

  return {
    isDba,
    loading,
  };
};

/**
 * 获取当前用户关联的所有组件类型列表（跨业务去重）
 * 用于个人工作台待办页面的 Tab 过滤
 */
export const useUserDbaComponents = () => {
  const components = ref<{ db_type: string; db_type_display: string }[]>([]);

  const { loading } = useRequest(getUserDbaComponents, {
    cacheKey: 'userDbaComponents',
    onSuccess(result) {
      components.value = result.component;
    },
  });

  return {
    components,
    loading,
  };
};
