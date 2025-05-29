import { useI18n } from 'vue-i18n';

import { execCopy, messageWarn } from '@utils';

export const useCopyMachineIp = () => {
  const { t } = useI18n();
  const copyAllIp = (machineList: { ip: string }[]) => {
    const ipList = machineList.map((item) => item.ip);
    if (ipList.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const copyNotAliveIp = (machineList: { host_info: { alive: number; ip: string } }[]) => {
    const ipList = machineList.reduce((result, item) => {
      if (!item.host_info.alive) {
        result.push(item.host_info.ip);
      }
      return result;
    }, [] as Array<string>);

    if (ipList.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }

    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  return {
    copyAllIp,
    copyNotAliveIp,
  };
};
