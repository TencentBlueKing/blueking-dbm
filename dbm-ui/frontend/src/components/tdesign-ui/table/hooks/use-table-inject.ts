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

import { computed, inject, type InjectionKey, provide, type Ref } from 'vue';

import type { IRegisteredColumnProps } from '../types/table';

export type ProvideTableFuncs = {
  addColumnProps: (id: string, columnProps: Ref<IRegisteredColumnProps>) => void;
  deleteColumn: (id: string) => void;
};
const TABLE_COLUMN_KEY: InjectionKey<ProvideTableFuncs> = Symbol('table-column-key');

export const useTableInject = () => computed(() => inject(TABLE_COLUMN_KEY));

export const useTableProvide = (data: ProvideTableFuncs) => {
  provide(TABLE_COLUMN_KEY, data);
};
