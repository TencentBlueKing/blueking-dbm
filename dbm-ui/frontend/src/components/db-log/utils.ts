import dayjs from 'dayjs';

export interface NodeLog {
  // 后端插入的提示行（如中间省略文案）：不展示行号和时间/级别前缀，原样输出
  ignore_line?: boolean;
  levelname: string;
  message: string;
  timestamp: number;
}

export const formatLogData = (data: NodeLog[] = [], isSetColor = true) => {
  const regex = /^##\[[a-z]+]/;
  return data.map((item) => {
    const { ignore_line: ignoreLine, levelname, message, timestamp } = item;
    // ignore_line 行不加时间/级别前缀
    if (ignoreLine) {
      return message.replace(/\n/g, '\r\n');
    }
    const time = timestamp ? dayjs(Number(timestamp)).format('YYYY-MM-DD HH:mm:ss') : '';
    if (!time && !levelname) {
      return message;
    }

    let rowText = regex.test(message)
      ? message.replace(regex, (match: string) => `${match}[${time} ${levelname}]`)
      : `[${time} ${levelname}] ${message}`;
    rowText = rowText.replace(/\n/g, '\r\n');
    if (!isSetColor) {
      return rowText;
    }

    // if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} info\]/.test(rowText)) {
    //   return `\x1b[32m${rowText}\x1b[0m`;
    // }

    if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} warn\]/i.test(rowText)) {
      return `\x1b[33m${rowText}\x1b[0m`;
    }

    if (/\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} error\]/i.test(rowText)) {
      return `\x1b[31m${rowText}\x1b[0m`;
    }

    return rowText;
  });
};
