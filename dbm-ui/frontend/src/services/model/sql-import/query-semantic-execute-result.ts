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
import SemanticData from '@services/model/sql-import/semantic-data';

export default class QuerySemanticExecuteResult {
  import_mode: string;
  semantic_data: SemanticData;
  sql_data_ready: boolean;

  constructor(payload = {} as QuerySemanticExecuteResult) {
    this.import_mode = payload.import_mode;
    this.semantic_data = payload.semantic_data;
    this.sql_data_ready = payload.sql_data_ready;
  }
}
