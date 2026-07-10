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
 */
export const isSearchKeywordMatch = (label: string, keyword: string) => {
  const keywordList = splitSearchKeyword(keyword).map((item) => item.toLowerCase());
  if (keywordList.length === 0) {
    return true;
  }

  const target = `${label ?? ''}`.toLowerCase();
  return keywordList.some((item) => target.includes(item));
};
