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

import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import { getMongoInstancesList } from '@services/source/mongodb';

// instancelist 单行（Mongo 实例）
export type MongoHostRow = MongodbInstanceModel;

// 透传给 getMongoInstancesList 的固定过滤参数（分页由组件内部管理）
export type MongoHostFetchParams = Partial<Omit<ServiceParameters<typeof getMongoInstancesList>, 'limit' | 'offset'>>;

export type DisableSelectMethod = (data: MongoHostRow) => boolean | string;
