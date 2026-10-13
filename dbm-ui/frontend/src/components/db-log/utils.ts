import dayjs from 'dayjs';

export interface NodeLog {
  levelname: string;
  message: string;
  timestamp: number;
}

export const formatLogData = (data: NodeLog[] = [], isSetColor = true) => {
  const regex = /^##\[[a-z]+]/;
  return data.map((item) => {
    const { levelname, message, timestamp } = item;
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
