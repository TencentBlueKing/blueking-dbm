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

import type { MySQLImportSQLFileDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// spider SQL变更执行
export function generateSpiderSqlExecuteCloneData(ticketData: TicketModel<MySQLImportSQLFileDetails>) {
  const { details } = ticketData;
  return Promise.resolve({
    backup: details.backup,
    charset: details.charset,
    ticket_mode: details.ticket_mode,
    import_mode: details.import_mode,
    cluster_ids: details.cluster_ids,
    execute_db_infos: details.execute_objects.map((item) => ({
      ...item,
      rowKey: random(),
    })),
    remark: ticketData.remark,
  });
}
