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

import * as XLSX from 'xlsx';

// 导出列宽按内容自适应的上下限（单位：字符宽度），避免列太窄看不全或单列过宽
const COLUMN_MIN_WIDTH = 10;
const COLUMN_MAX_WIDTH = 60;

// 文本显示宽度：中文等全角字符按 2 个字符宽计算，多行文本取最长一行
const getTextWidth = (value: unknown) => {
  if (value === null || value === undefined) {
    return 0;
  }
  return Math.max(
    ...String(value)
      .split('\n')
      .map((line) => Array.from(line).reduce((width, char) => width + (char.charCodeAt(0) > 255 ? 2 : 1), 0)),
  );
};

/**
 * 用二维数组生成 Sheet（表头作为普通行放在数组里），列宽按内容自适应
 */
export const createWorkSheet = (rows: unknown[][]) => {
  const workSheet = XLSX.utils.aoa_to_sheet(rows);
  const columnCount = Math.max(0, ...rows.map((row) => row.length));

  // 列宽取该列所有单元格中最宽的值，留 2 个字符余量，并限制在上下限内
  workSheet['!cols'] = Array.from({ length: columnCount }, (_, colIndex) => {
    const contentWidth = Math.max(0, ...rows.map((row) => getTextWidth(row[colIndex])));
    return {
      wch: Math.min(Math.max(contentWidth + 2, COLUMN_MIN_WIDTH), COLUMN_MAX_WIDTH),
    };
  });

  return workSheet;
};

/**
 * 下载 xlsx 文件
 */
export const downloadWorkBook = (workBook: XLSX.WorkBook, fileName: string) => {
  // 不用 XLSX.writeFile：它会往 body 插入 a 标签并模拟点击，该点击冒泡到 body 后会被
  // dbm-table-detail-dialog 的「点击外部关闭」判定为外部点击，导致单据详情弹窗被关闭
  const blob = new Blob([XLSX.write(workBook, { bookType: 'xlsx', type: 'array' })], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  // 只拦截冒泡，不阻止默认行为，下载照常触发
  link.addEventListener('click', (event) => event.stopPropagation());
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // 立即释放在部分浏览器（如 Firefox）下会导致下载失败，与 SheetJS 自身实现一致延后 60s 回收
  setTimeout(() => URL.revokeObjectURL(url), 60 * 1000);
};
