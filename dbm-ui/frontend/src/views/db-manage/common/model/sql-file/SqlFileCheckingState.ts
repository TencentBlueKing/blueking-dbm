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
import SqlFileState from './SqlFileState';
import type SqlFileSuccessState from './SqlFileSuccessState';
import type SqlFileUploadFailState from './SqlFileUploadFailState';

export default class SqlFileCheckingState extends SqlFileState {
  // constructor(payload: SqlFile) {
  //   super(payload);
  // }
  get state() {
    return SqlFile.CHECKING;
  }

  grammarCheckFailed(checkResult: Record<string, GrammarCheckModel>, sqlState: SqlFileCheckFailState) {
    const [realFilePath] = Object.keys(checkResult);
    const [fileCheckResult] = Object.values(checkResult);

    this.sqlFile.content = fileCheckResult.content;
    this.sqlFile.messageList = fileCheckResult.messageList;
    this.sqlFile.grammarCheck = fileCheckResult;
    this.sqlFile.realFilePath = realFilePath;

    this.sqlFile.setState(sqlState);
  }

  grammarCheckSuccessed(checkResult: Record<string, GrammarCheckModel>, sqlState: SqlFileSuccessState) {
    const [realFilePath] = Object.keys(checkResult);
    const [fileCheckResult] = Object.values(checkResult);

    this.sqlFile.content = fileCheckResult.content;
    this.sqlFile.messageList = fileCheckResult.messageList;
    this.sqlFile.grammarCheck = fileCheckResult;
    this.sqlFile.realFilePath = realFilePath;

    this.sqlFile.setState(sqlState);
  }

  uploadFailed(
    sqlState: SqlFileUploadFailState,
    data?: Pick<SqlFile, 'content' | 'realFilePath' | 'uploadErrorMessage'>,
  ) {
    if (data) {
      this.sqlFile.content = data.content;
      this.sqlFile.realFilePath = data.realFilePath;
      this.sqlFile.uploadErrorMessage = data.uploadErrorMessage;
    }

    this.sqlFile.setState(sqlState);
  }
}
