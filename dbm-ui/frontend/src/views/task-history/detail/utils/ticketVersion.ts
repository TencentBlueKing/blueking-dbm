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

import type { InjectionKey, Ref } from 'vue';

import { getTicketVersion } from '@services/source/ticket';

/**
 * 任务流所属单据 id（flow_info.uid）。
 *
 * 确认继续要带单据内容版本，画布节点操作、节点详情、批量操作三处入口都要用
 */
export const ticketIdInjectionKey: InjectionKey<Ref<number>> = Symbol('ticketId');

/**
 * 任务流页面不展示单据内容，执行阶段也不会再改单，确认继续前取单据当前版本即可
 */
export const fetchTicketVersion = (ticketId: number) =>
  getTicketVersion({ ticket_ids: String(ticketId) }).then((data) => data[ticketId] ?? null);
