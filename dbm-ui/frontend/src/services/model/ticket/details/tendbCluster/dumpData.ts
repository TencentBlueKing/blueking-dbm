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

import type { DetailBase, DetailClusters } from '../common';

interface DumpDataBase extends DetailBase {
  charset: string;
  cluster_id: number;
  clusters: DetailClusters;
}

export interface TableDumpData extends DumpDataBase {
  databases: string[];
  dump_data: boolean; // 是否导出表数据
  dump_schema: boolean; // 是否导出表结构
  export_mode?: 'table';
  tables: string[];
  tables_ignore: string[];
  where: string;
}

export interface SqlDumpData extends DumpDataBase {
  export_mode: 'sql';
  result_format: 'txt' | 'csv';
  sql_filename: string;
  sql_path: string;
}

export type DumpData = TableDumpData | SqlDumpData;

export interface DumpDataDetails extends DetailBase {
  clusters: DetailClusters;
  infos: DumpData[];
}
