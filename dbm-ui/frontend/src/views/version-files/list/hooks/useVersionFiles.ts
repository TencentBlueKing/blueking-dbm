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

import { Message } from 'bkui-vue';
import type { Ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  deletePackage,
  getPackages,
} from '@services/source/package';

import { useInfo } from '@hooks';

import type { IState, TypeParams } from '../components/types';

/**
 * 列表基础操作
 * @param state 列表基础 state
 * @param typeParams 请求类型参数
 */
export const useVersionFiles = (state: IState, typeParams: Ref<TypeParams>) => {
  const { t } = useI18n();

  /**
   * 获取版本文件列表
   */
  function fetchPackages() {
    state.isLoading = true;
    getPackages({
      keyword: state.search,
      ...typeParams.value,
      ...state.pagination.getFetchParams(),
    }, {
      permission: 'catch',
    })
      .then((res) => {
        state.pagination.count = res.count;
        state.data = res.results;
        state.isAnomalies = false;
      })
      .catch(() => {
        state.pagination.count = 0;
        state.data = [];
        state.isAnomalies = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleChangePage(value: number) {
    state.pagination.current = value;
    fetchPackages();
  }

  function handeChangeLimit(value: number) {
    state.pagination.limit = value;
    handleChangePage(1);
  }

  /**
   * 删除版本
   */
  function handleConfirmDelete(data: ServiceReturnType<typeof getPackages>['results'][number]) {
    useInfo({
      title: t('确认删除'),
      content: t('确认删除xx', [data.name]),
      onConfirm: () => deletePackage({ id: data.id })
        .then(() => {
          Message({
            message: t('删除成功'),
            theme: 'success',
          });
          handleChangePage(1);
          return true;
        })
        .catch(() => false),
    });
  }

  return {
    fetchPackages,
    handleChangePage,
    handeChangeLimit,
    handleConfirmDelete,
  };
};
