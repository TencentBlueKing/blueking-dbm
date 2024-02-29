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

export default class GrammarCheck {
  bancommand_warnings: Array<{
    command_type: string;
    line: number;
    sqltext: string;
    warn_info: string;
  }>;
  content: string;
  highrisk_warnings: Array<{
    command: string;
    line: number;
    sqltext: string;
    warn_info: string;
  }>;
  raw_file_name: string;
  sql_path: string;
  syntax_fails: Array<{
    error_code: number;
    error_msg: string;
    line: number;
    sqltext: string;
  }>;

  constructor(payload = {} as GrammarCheck) {
    this.bancommand_warnings = payload.bancommand_warnings || [];
    this.content = payload.content;
    this.highrisk_warnings = payload.highrisk_warnings || [];
    this.raw_file_name = payload.raw_file_name;
    this.sql_path = payload.sql_path;
    this.syntax_fails = payload.syntax_fails || [];
  }

  get isError() {
    return this.syntax_fails.length > 0 || this.bancommand_warnings.length > 0;
  }

  get messageList() {
    const result: Array<{ type: 'warning' | 'error'; line: number; message: string }> = [];

    this.bancommand_warnings.forEach((item) => {
      result.push({
        type: 'error',
        line: item.line,
        message: item.warn_info,
      });
    });

    this.syntax_fails.forEach((item) => {
      result.push({
        type: 'error',
        line: item.line,
        message: item.error_msg,
      });
    });

    this.highrisk_warnings.forEach((item) => {
      result.push({
        type: 'warning',
        line: item.line,
        message: item.warn_info,
      });
    });
    return result;
  }
}
