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

import type BackupLogRecordModel from '@services/model/tendbcluster/backup-log-record';

import type { DetailBase, DetailClusters } from '../../common';

// 新机回档由后端派生部署参数，不复用原地回档的资源规格协议。
export interface RollbackNewHost extends DetailBase {
  clusters?: DetailClusters;
  ignore_check_db?: boolean;
  infos: [
    {
      affect_database_list?: string[];
      backupinfo: {
        priv?: Record<string, unknown>;
      } & Partial<Omit<BackupLogRecordModel, 'database_list' | 'backup_type_list'>> &
        Pick<BackupLogRecordModel, 'database_list' | 'backup_type_list'>;
      cluster_id: number;
      databases: string[];
      databases_ignore?: string[];
      label?: {
        label_names: string[];
        labels: number[];
      };
      rollback_time?: string;
      rollback_type: 'REMOTE_AND_TIME' | 'REMOTE_AND_BACKUPID' | 'LOCAL_AND_TIME' | 'LOCAL_AND_BACKUPID';
      tables: string[];
      tables_ignore?: string[];
    },
  ];
  ip_source?: 'resource_pool';
}
