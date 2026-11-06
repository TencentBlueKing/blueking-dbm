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

import { t } from '@locales/index';

import { getSQLFilename } from './getSQLFilename';

interface ValidateResult {
  message: string;
  valid: boolean;
}

// 与后端 MAX_UPLOAD_SQL_FILE_NAME_LENGTH 保持一致
const SQL_FILENAME_MAX_LENGTH = 120;
// 与后端校验一致：仅允许字母、数字、中文、下划线、连字符和点
const SQL_FILENAME_CHAR_REG = /^[A-Za-z0-9_\-.\u4e00-\u9fa5]+$/;
const SQL_FILENAME_EXT_REG = /\.sql$/i;
// 路径中不允许出现反斜杠与空白字符
const SQL_FILE_PATH_ILLEGAL_REG = /[\\\s]/;

const success = (): ValidateResult => ({ message: '', valid: true });
const fail = (message: string): ValidateResult => ({ message, valid: false });

/**
 * 是否包含控制字符（0x00-0x1F、0x7F）
 */
const hasControlChar = (value: string) =>
  Array.from(value).some((char) => {
    const code = char.codePointAt(0) as number;
    return code < 32 || code === 127;
  });

/**
 * 校验 SQL 文件所在目录路径
 * 允许 `/` 作为目录分隔符，禁止路径穿越、反斜杠、空白与控制字符
 */
export const validateSqlFilePath = (path: string): ValidateResult => {
  if (path.includes('..') || SQL_FILE_PATH_ILLEGAL_REG.test(path) || hasControlChar(path)) {
    return fail(t('文件路径非法'));
  }
  return success();
};

/**
 * 校验 SQL 文件名
 * 兼容后端返回的 `<前缀>_dbmrpt_<原文件名>`：整体禁止路径分隔与穿越，原文件名部分按白名单校验
 */
export const validateSqlFilename = (filename: string): ValidateResult => {
  if (!filename) {
    return fail(t('文件名不能为空'));
  }
  if (filename.includes('..')) {
    return fail(t('文件名不能包含 ..'));
  }
  if (filename.includes('/') || !validateSqlFilePath(filename).valid) {
    return fail(t('文件名包含非法字符，仅允许字母、数字、中文、下划线、连字符和点'));
  }

  const rawFilename = getSQLFilename(filename);
  if (!SQL_FILENAME_CHAR_REG.test(rawFilename)) {
    return fail(t('文件名包含非法字符，仅允许字母、数字、中文、下划线、连字符和点'));
  }
  if (!SQL_FILENAME_EXT_REG.test(rawFilename)) {
    return fail(t('仅支持 .sql 文件'));
  }
  if (rawFilename.length > SQL_FILENAME_MAX_LENGTH) {
    return fail(t('文件名长度不能超过n个字符', { n: SQL_FILENAME_MAX_LENGTH }));
  }
  return success();
};

/**
 * 提交前校验回填的文件目录与文件列表，返回第一个不通过项的提示
 */
export const validateSqlFiles = (path: string, fileNameList: string[]): ValidateResult => {
  const pathResult = validateSqlFilePath(path);
  if (!pathResult.valid) {
    return fail(t('SQL 文件【name】校验不通过：reason', { name: path, reason: pathResult.message }));
  }

  for (const fileName of fileNameList) {
    const fileResult = validateSqlFilename(fileName);
    if (!fileResult.valid) {
      return fail(
        t('SQL 文件【name】校验不通过：reason', { name: getSQLFilename(fileName), reason: fileResult.message }),
      );
    }
  }
  return success();
};
