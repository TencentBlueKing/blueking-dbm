import { computed } from 'vue';

const parsePythonDict = (originString: string) => {
  const result = originString.match(/\[[\s\S]*\]/);
  if (!result) {
    return null;
  }
  let resultString = result[0];

  // 1. 处理 None/True/False
  resultString = resultString
    .replace(/\bNone\b/g, 'null')
    .replace(/\bTrue\b/g, 'true')
    .replace(/\bFalse\b/g, 'false');

  // 2. 给 key 加双引号（如果没加）
  resultString = resultString.replace(/([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:/g, '$1"$2":');

  // 3. 处理字符串值里的单引号（转义内部单引号）
  // 这里简化：将最外层的单引号替换成双引号，但保留内部已转义的
  resultString = resultString.replace(/'([^'\\]*(\\.[^'\\]*)*)'/g, (_, content) => {
    // 对 content 里的双引号转义
    const escaped = content.replace(/"/g, '\\"');
    return `"${escaped}"`;
  });

  try {
    return JSON.parse(resultString);
  } catch (e) {
    console.error('解析失败', e);
    return null;
  }
};

export const useImportResourceErrorMessage = () => {
  const errorHostList = shallowRef<string[]>([]);
  const errorMessageList = shallowRef<{ ips: string[]; message: string }[]>([]);

  const errorHostMap = computed(() => Object.fromEntries(errorHostList.value.map((ip) => [ip, true])));

  const handleChange = (message: string) => {
    const messageList: {
      ips: string[];
      message: string;
      tickets?: {
        bk_biz_id: number;
        id: number;
      }[];
    }[] = parsePythonDict(message) || [];
    errorHostList.value = messageList.flatMap((item) => item.ips);
    errorMessageList.value = messageList;
  };

  return {
    errorHostList,
    errorHostMap,
    errorMessageList,
    handleChange,
  };
};
