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

import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(customParseFormat);

export type DatePickerType = 'date' | 'daterange' | 'datetime' | 'datetimerange' | 'month' | 'year';

export type SelectionMode = 'date' | 'month' | 'year';

/** 面板当前展示的表格 */
export type TableType = 'date' | 'month' | 'year';

export type TimePart = 'hours' | 'minutes' | 'seconds';

export type DateValue = Date | number | string | null | undefined;

export type PickerValue = DateValue | DateValue[];

/** 组件内部统一使用 Date 数组：单选长度 1，范围长度 2 */
export type InternalValue = (Date | null)[];

export type DisabledDate = (date: Date) => boolean;

export interface DatePickerShortcut {
  onClick?: (shortcut: DatePickerShortcut, index: number) => void;
  text: string;
  /** 与 bk-date-picker 一致，支持函数（每次点击重新计算）或直接传值 */
  value?: (() => Date | Date[]) | Date | Date[];
}

export interface RangeState {
  from: Date | null;
  selecting: boolean;
  to: Date | null;
}

export interface PickOptions {
  /** 选择后保持弹层展开（时间面板滚动选择） */
  keepOpen?: boolean;
  shortcut?: DatePickerShortcut;
  type: string;
}

/** 取快捷项的值：函数写法执行后返回，直接值原样返回 */
export const getShortcutValue = (shortcut?: DatePickerShortcut) =>
  typeof shortcut?.value === 'function' ? shortcut.value() : shortcut?.value;

export const RANGE_SEPARATOR = ' - ';

// format 统一使用 dayjs 写法（YYYY、DD 大写），直接交给 dayjs 格式化与解析
export const DEFAULT_FORMATS: Record<DatePickerType, string> = {
  date: 'YYYY-MM-DD',
  daterange: 'YYYY-MM-DD',
  datetime: 'YYYY-MM-DD HH:mm:ss',
  datetimerange: 'YYYY-MM-DD HH:mm:ss',
  month: 'YYYY-MM',
  year: 'YYYY',
};

export const isRangeType = (type: DatePickerType) => type.endsWith('range');

export const getSelectionMode = (type: DatePickerType): SelectionMode => {
  if (type === 'month' || type === 'year') {
    return type;
  }
  return 'date';
};

export const formatDate = (date: Date | null, format: string) => (date ? dayjs(date).format(format) : '');

/** 输入框展示文案，范围类型起止任一为空时展示为空 */
export const formatValue = (dates: InternalValue, type: DatePickerType, format: string) => {
  if (isRangeType(type)) {
    const [start, end] = dates;
    return start && end ? `${formatDate(start, format)}${RANGE_SEPARATOR}${formatDate(end, format)}` : '';
  }
  return formatDate(dates[0], format);
};

/** 外部传入值转 Date：字符串先按 format 严格解析，失败再交给 dayjs 宽松解析（兼容 ISO 等格式） */
const toDate = (value: DateValue, format: string): Date | null => {
  // 与 bk-date-picker 一致，0、''、null、undefined 视为空
  if (!value) {
    return null;
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : new Date(value);
  }
  if (typeof value === 'number') {
    return new Date(value);
  }
  const text = value.trim();
  if (!text) {
    return null;
  }
  const strictDate = dayjs(text, format, true);
  if (strictDate.isValid()) {
    return strictDate.toDate();
  }
  const looseDate = dayjs(text);
  return looseDate.isValid() ? looseDate.toDate() : null;
};

export const parseValue = (value: PickerValue, type: DatePickerType, format: string): InternalValue => {
  if (isRangeType(type)) {
    let list: DateValue[] = [];
    if (Array.isArray(value)) {
      list = value;
    } else if (typeof value === 'string' && value) {
      list = value.split(RANGE_SEPARATOR);
    }
    const start = toDate(list[0], format);
    const end = toDate(list[1], format);
    return start && end ? [start, end] : [null, null];
  }
  return [toDate(Array.isArray(value) ? value[0] : value, format)];
};

/** 手动输入的文案只按 format 严格解析，任一部分不合法返回 null */
export const parseInputText = (text: string, type: DatePickerType, format: string): InternalValue | null => {
  const parts = isRangeType(type) ? text.split(RANGE_SEPARATOR) : [text];
  if (parts.length !== (isRangeType(type) ? 2 : 1)) {
    return null;
  }
  const dates = parts.map((item) => dayjs(item.trim(), format, true));
  if (dates.some((item) => !item.isValid())) {
    return null;
  }
  return dates.map((item) => item.toDate());
};

export const clearHours = (date: Date) => {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  return result.getTime();
};

export const getDayEnd = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59);

/** 当天零点 */
export const initTime = () => new Date(clearHours(new Date()));

/** 月份序号，用于比较两个日期所在月份的先后 */
export const getMonthIndex = (date: Date) => date.getFullYear() * 12 + date.getMonth();

/** 面板日期统一取当月 1 号，避免 31 号跨月时溢出到下下个月 */
export const shiftMonth = (date: Date, months: number) => new Date(date.getFullYear(), date.getMonth() + months, 1);

export const setTimePart = (date: Date, part: TimePart, value: number) => {
  const result = new Date(date);
  if (part === 'hours') {
    result.setHours(value);
  } else if (part === 'minutes') {
    result.setMinutes(value);
  } else {
    result.setSeconds(value);
  }
  return result;
};

/** 时间面板中被 disabledDate 禁用的时、分、秒：逐个替换当前时间的对应部分后判断 */
export const getDisabledTimes = (date: Date | null, disabledDate?: DisabledDate) => {
  const result: Record<TimePart, number[]> = { hours: [], minutes: [], seconds: [] };
  if (!date || !disabledDate) {
    return result;
  }
  const maxMap: Record<TimePart, number> = { hours: 24, minutes: 60, seconds: 60 };
  (Object.keys(maxMap) as TimePart[]).forEach((part) => {
    for (let value = 0; value < maxMap[part]; value++) {
      if (disabledDate(setTimePart(date, part, value))) {
        result[part].push(value);
      }
    }
  });
  return result;
};

const getIntlLocale = (locale: string) => (locale.startsWith('zh') ? 'zh-CN' : 'en-US');

/** 星期表头，从周日开始 */
export const getWeekdayLabels = (locale: string) => {
  const formatter = new Intl.DateTimeFormat(getIntlLocale(locale), {
    weekday: locale.startsWith('zh') ? 'narrow' : 'short',
  });
  // 2023-01-01 是周日
  return Array.from({ length: 7 }, (_, index) => formatter.format(new Date(2023, 0, 1 + index)));
};

export const getMonthLabels = (locale: string) => {
  const formatter = new Intl.DateTimeFormat(getIntlLocale(locale), { month: 'short' });
  return Array.from({ length: 12 }, (_, index) => formatter.format(new Date(2023, index, 1)));
};
