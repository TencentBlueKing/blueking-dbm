import { t } from '@locales/index';

import { messageSuccess } from './message';

export const downloadText = (filename: string, text: string) => {
  const element = document.createElement('a');
  const blob = new Blob([text]);
  element.href = URL.createObjectURL(blob);

  element.setAttribute('protocol', 'https');
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);

  messageSuccess(t('下载成功'));
};

