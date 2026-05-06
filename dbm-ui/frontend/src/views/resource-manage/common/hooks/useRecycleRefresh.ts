import { Message } from 'bkui-vue';
import { useI18n } from 'vue-i18n';

import type { transferMachinePool } from '@services/source/dbdirty';

import { useSystemEnviron } from '@stores';

export const useRecycleRefresh = (options: { onSucess: () => void }) => {
  const { t } = useI18n();
  const systemEnvironStore = useSystemEnviron();

  const handleRecycleRefresh = (data: ServiceReturnType<typeof transferMachinePool>) => {
    if (data.hcm_recycle_id) {
      const { BK_HCM_URL, RESOURCE_INDEPENDENT_BIZ } = systemEnvironStore.urls;
      const targetHref = `${BK_HCM_URL}/#/business/applications?bizs=${RESOURCE_INDEPENDENT_BIZ}&filter=order_id=${data.hcm_recycle_id}&type=host_recycle`;
      Message({
        actions: [
          {
            disabled: true,
            id: 'details',
          },
          {
            disabled: true,
            id: 'fix',
          },
          {
            id: 'assistant',
            render: () =>
              h(
                'a',
                {
                  href: targetHref,
                  target: '_blank',
                },
                ` ${t('查看详情')}`,
              ),
          },
        ],
        delay: 6000,
        dismissable: false,
        message: {
          code: '',
          overview: data.message,
          suggestion: '',
        },
        theme: 'success',
      });
    }

    options.onSucess();
  };

  return {
    handleRecycleRefresh,
  };
};
