/**
 * 校验语句是否为完整的脚本语句
 * @example const isValid = validateBrackets('db.find({"{"})');
 * console.log(isValid); // true
 * @param input 语句
 * @returns boolean
 */
export function validateBrackets(input: string): boolean {
  const stack: string[] = [];
  const pairs: Record<string, string> = {
    ')': '(',
    ']': '[',
    '}': '{',
  };

  // 过滤掉注释内容（包括 // 和 /* */）
  const withoutComments = input
    .replace(/\/\/.*$/gm, '') // 去掉单行注释
    .replace(/\/\*[\s\S]*?\*\//g, ''); // 去掉多行注释

  // 过滤掉成对的引号内容
  const filteredInput = withoutComments.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, '');

  for (const char of filteredInput) {
    if (['(', '[', '{'].includes(char)) {
      stack.push(char); // 开括号入栈
    } else if ([')', ']', '}'].includes(char)) {
      if (stack.pop() !== pairs[char]) {
        return false; // 括号不匹配
      }
    }
  }

  return stack.length === 0; // 栈为空表示所有括号匹配
}
