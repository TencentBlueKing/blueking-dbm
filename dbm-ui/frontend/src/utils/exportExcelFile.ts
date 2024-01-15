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

import {
  utils,
  type WorkBook,
  writeFile,
} from 'xlsx';

/**
 * 导出 excel 文件
 * @param array      数据源数组
 * @param colsWidths 列宽设置
 * @param sheetName  sheet名
 * @param fileName   excel名
 */
export function exportExcelFile(
  array: any[],
  colsWidths: { width: number }[],
  sheetName = 'sheet',
  fileName = 'example.xlsx',
) {
  const jsonWorkSheet = utils.json_to_sheet(array);
  jsonWorkSheet['!cols'] = colsWidths;

  const workBook: WorkBook = {
    SheetNames: [sheetName],
    Sheets: {
      [sheetName]: jsonWorkSheet,
    },
  };
  return writeFile(workBook, fileName);
}
