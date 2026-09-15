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
