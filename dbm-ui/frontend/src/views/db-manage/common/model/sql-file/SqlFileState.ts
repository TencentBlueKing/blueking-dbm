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

import type GrammarCheckModel from '@services/model/sql-import/grammar-check';

import SqlFile from './SqlFile';
import type SqlFileCheckFailState from './SqlFileCheckFailState';
import type SqlFileCheckingState from './SqlFileCheckingState';
import type SqlFileSuccessState from './SqlFileSuccessState';
import type SqlFileUncheckState from './SqlFileUncheckState';
import type SqlFileUploadFailState from './SqlFileUploadFailState';

export default class SqlFileState {
  sqlFile: SqlFile;

  constructor(payload: SqlFile) {
    this.sqlFile = payload;
  }

  get state() {
    return '';
  }

  grammarCheckFailed(_checkResult: Record<string, GrammarCheckModel>, _sqlState: SqlFileCheckFailState) {}
  grammarCheckStart(_state: SqlFileCheckingState) {}
  grammarCheckSuccessed(_checkResult: Record<string, GrammarCheckModel>, _sqlState: SqlFileSuccessState) {}
  reEdit(_sqlState: SqlFileUncheckState) {}
  toEdited() {}
  uploadFailed(
    _sqlState: SqlFileUploadFailState,
    _data?: Pick<SqlFile, 'content' | 'realFilePath' | 'uploadErrorMessage'>,
  ) {}
}
