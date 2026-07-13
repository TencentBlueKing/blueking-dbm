/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and limitations under the License.
 */

/** Excel 解析配置 */
export interface ParseExcelOptions {
  /** 最大行数限制（含表头），默认 1000 */
  maxRows?: number;
}

/**
 * 纯前端解析 Excel 文件，返回二维数组（每行为一个数组）
 * @param file Excel 文件（.xlsx / .xls）
 * @param options 解析配置
 * @returns 二维数组，第一行为表头
 */
export const parseExcelFile = (file: File, options?: ParseExcelOptions): Promise<unknown[]> => {
  const { maxRows = 1000 } = options || {};
  return new Promise((resolve, reject) => {
    import('xlsx')
      .then((XLSX) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const data = new Uint8Array(e.target?.result as ArrayBuffer);
            const workbook = XLSX.read(data, { type: 'array' });
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            const jsonData: unknown[] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

            if (jsonData.length > maxRows + 1) {
              reject(new Error(`Excel file exceeds maximum ${maxRows} rows`));
              return;
            }

            resolve(jsonData);
          } catch {
            reject(new Error('Failed to parse Excel file'));
          }
        };
        reader.onerror = () => {
          reject(new Error('Failed to read Excel file'));
        };
        reader.readAsArrayBuffer(file);
      })
      .catch(() => {
        reject(new Error('xlsx library is not available'));
      });
  });
};

/** 判断 accept 是否为 Excel 类型（.xlsx / .xls） */
export const isExcelAccept = (accept?: string): boolean => {
  if (!accept) return false;
  return accept.split(',').some((ext) => {
    const trimmed = ext.trim().toLowerCase();
    return trimmed === '.xlsx' || trimmed === '.xls';
  });
};
