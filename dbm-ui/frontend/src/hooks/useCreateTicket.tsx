import InfoBox from 'bkui-vue/lib/info-box';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { createTicket } from '@services/source/ticket';

import { messageError, messageSuccess } from '@utils';

export const useCreateTicket = (params: Record<string, any>) => {
  const { t, locale } = useI18n();
  const router = useRouter();

  createTicket(params)
    .then(() => messageSuccess(t('单据创建成功')))
    .catch((e) => {
      const { code, data } = e;
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;

        InfoBox({
          title: t('是否继续提交单据'),
          content: () => {
            const route = router.resolve({
              name: 'bizTicketManage',
              query: {
                id,
              },
            });

            if (locale.value === 'en') {
              return (
                <span>
                  You have already submitted a
                  <a
                    href={route.href}
                    target='_blank'>
                    {' '}
                    ticket[{id}]{' '}
                  </a>
                  with the same target cluster, continue?
                </span>
              );
            }

            return (
              <span>
                你已提交过包含相同目标集群的
                <a
                  href={route.href}
                  target='_blank'>
                  单据[{id}]
                </a>
                ，是否继续？
              </span>
            );
          },
          confirmText: t('继续提单'),
          cancelText: t('取消提单'),
          onConfirm: async () => {
            try {
              await createTicket({
                ...params,
                ignore_duplication: true,
              });
            } catch (e: any) {
              messageError(e?.message);
            }
          },
        });
      }

      messageError(e.message);
    });
};
