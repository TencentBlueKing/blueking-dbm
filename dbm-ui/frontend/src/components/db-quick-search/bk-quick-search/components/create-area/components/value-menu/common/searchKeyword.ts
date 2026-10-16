import { match } from 'pinyin-pro';

// 搜索关键字分隔符：全角/半角竖线、全角/半角分号
const SEARCH_KEYWORD_SEPARATOR = /[|｜;；]/;

/**
 * 将输入的搜索文本按分隔符（｜ | ； ;）拆分为多个关键字
 */
export const splitSearchKeyword = (keyword: string) =>
  `${keyword ?? ''}`
    .split(SEARCH_KEYWORD_SEPARATOR)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

/**
 * 判断 label 是否命中搜索关键字（支持按 ｜ | ； ; 分隔的多个值，命中任意一个即可）
 * 除原文外，还支持拼音全拼与首字母匹配，多音字的各读音都参与匹配
 * @example isSearchKeywordMatch('重建中', 'cjz') // true
 */
export const isSearchKeywordMatch = (label: string, keyword: string) => {
  const keywordList = splitSearchKeyword(keyword).map((item) => item.toLowerCase());
  if (keywordList.length === 0) {
    return true;
  }

  const source = `${label ?? ''}`;
  const target = source.toLowerCase();
  return keywordList.some(
    (item) =>
      target.includes(item) ||
      // 拼音匹配：每个字可按全拼或拼音前缀连续命中
      Boolean(match(source, item, { continuous: true, precision: 'start' })),
  );
};
