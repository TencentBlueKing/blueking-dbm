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

import SqlFileCheckFailState from './SqlFileCheckFailState';
import SqlFileCheckingState from './SqlFileCheckingState';
import SqlFileState from './SqlFileState';
import SqlFileSuccessState from './SqlFileSuccessState';
import SqlFileUncheckState from './SqlFileUncheckState';
import SqlFileUploadFailState from './SqlFileUploadFailState';

export default class SqlFile {
  static CHECK_FAIL = 'CHECK_FAIL';
  static CHECKING = 'CHECKING';
  static SUCCESS = 'SUCCESS';
  static UNCHEKED = 'UNCHEKED';
  static UPLOAD_FAIL = 'UPLOAD_FAIL';

  content: string;
  currentState!: SqlFileState;
  file: File | null;
  grammarCheck?: GrammarCheckModel;
  messageList: GrammarCheckModel['messageList'];
  realFilePath: string;
  sqlFileCheckFailState: SqlFileCheckFailState;
  sqlFileCheckingState: SqlFileCheckingState;
  sqlFileSuccessState: SqlFileSuccessState;
  sqlFileUncheckState: SqlFileUncheckState;
  sqlFileUploadFailState: SqlFileUploadFailState;
  state: string;
  uploadErrorMessage: string;

  constructor(payload = {} as Partial<Pick<SqlFile, 'content' | 'realFilePath' | 'file'>>) {
    this.content = payload.content || '';
    this.file = payload.file || null;
    this.grammarCheck = undefined;
    this.state = '';
    this.messageList = [];
    this.realFilePath = payload.realFilePath || '';
    this.uploadErrorMessage = '';

    this.sqlFileCheckingState = new SqlFileCheckingState(this);
    this.sqlFileCheckFailState = new SqlFileCheckFailState(this);
    this.sqlFileUploadFailState = new SqlFileUploadFailState(this);
    this.sqlFileSuccessState = new SqlFileSuccessState(this);
    this.sqlFileUncheckState = new SqlFileUncheckState(this);

    this.setState(this.sqlFileUncheckState);
  }

  grammarCheckFailed(checkResult: Record<string, GrammarCheckModel>) {
    this.currentState.grammarCheckFailed(checkResult, this.sqlFileCheckFailState);
  }

  grammarCheckStart() {
    this.currentState.grammarCheckStart(this.sqlFileCheckingState);
  }

  grammarCheckSuccessed(checkResult: Record<string, GrammarCheckModel>) {
    this.currentState.grammarCheckSuccessed(checkResult, this.sqlFileSuccessState);
  }

  reEdit() {
    this.grammarCheck = undefined;
    this.currentState.reEdit(this.sqlFileUncheckState);
  }

  setState(state: SqlFileState) {
    this.currentState = state;
    this.state = state.state;
  }

  toEdited() {
    this.currentState.toEdited();
  }

  uploadFailed(data?: Pick<SqlFile, 'content' | 'realFilePath' | 'uploadErrorMessage'>) {
    this.currentState.uploadFailed(this.sqlFileUploadFailState, data);
  }
}
