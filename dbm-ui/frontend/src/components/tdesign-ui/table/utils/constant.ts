/*
 * Tencent is pleased to support the open source community by making
 * 蓝鲸智云PaaS平台 (BlueKing PaaS) available.
 *
 * Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
 *
 * 蓝鲸智云PaaS平台 (BlueKing PaaS) is licensed under the MIT License.
 *
 * License for 蓝鲸智云PaaS平台 (BlueKing PaaS):
 *
 * ---------------------------------------------------
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
 * to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
 * the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
 * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */

/* Table自定义配置列 */
export const BKUI_SETTINGS_COLUMN_NAME = '__col_setting__';

/* Table自定义操作咧 */
export const BKUI_COLUMN_ROW_OPERATION_KEY = 'row-operation';

/* Table-Column 的 id 属性 */
export const TABLE_COLUMN_ID_ATTRIBUTE = '__table_column_id__';

/* Table 组件的 ref name */
export const TABLE_REF_NAME = 'tableRef';

/* Table 组件的default slot ref name */
export const TABLE_DEFAULT_REF_NAME = 'tableDefaultRef';

/* tdesign 的 row-select 列 */
export const COLUMN_ROW_SELECT_KEY = 'row-select';

/* tdesign 的 drag 列 */
export const COLUMN_DRAG_KEY = 'drag';

/* tdesign 的 serial-number 列 */
export const COLUMN_SERIAL_NUMBER_KEY = 'serial-number';

export const BUILT_IN_COLUMN_KEYS = [
  COLUMN_ROW_SELECT_KEY,
  COLUMN_DRAG_KEY,
  COLUMN_SERIAL_NUMBER_KEY,
  BKUI_COLUMN_ROW_OPERATION_KEY,
].concat(BKUI_SETTINGS_COLUMN_NAME); // 确保设置列在最后一列
