/**
 * 校验语句是否为完整的脚本语句
 * @example const isValid = validateBrackets("function test() { return ['value']; }");
console.log(isValid); // true
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

  for (const char of input) {
    if (["'", '"', '(', '[', '{'].includes(char)) {
      // Handle quotes: check if the top of the stack is the same quote
      if ((char === "'" || char === '"') && stack[stack.length - 1] === char) {
        stack.pop(); // Closing quote
      } else {
        stack.push(char); // Opening bracket or quote
      }
    } else if ([')', ']', '}'].includes(char)) {
      if (stack.pop() !== pairs[char]) {
        return false; // Mismatched bracket
      }
    }
  }

  return stack.length === 0; // Stack should be empty if all pairs are matched
}
