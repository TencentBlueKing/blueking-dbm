import InfoBox from 'bkui-vue/lib/info-box';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { createTicketNew } from '@services/source/ticket';

import type { TicketTypes } from '@common/const';

import { messageError } from '@utils';

export function useCreateTicket<T>(ticketType: TicketTypes, options?: { onSuccess?: (ticketId: number) => void }) {
  const loading = ref(false);
  const router = useRouter();
  const { t, locale } = useI18n();

  const run = async (formData: { details: T; remark: string; ignore_duplication?: boolean }) => {
    const params = {
      ticket_type: ticketType,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      ...formData,
    };
    try {
      loading.value = true;
      const { id: ticketId } = await createTicketNew<T>(params);
      if (options?.onSuccess) {
        options.onSuccess(ticketId);
      } else {
        router.push({
          name: ticketType,
          params: {
            page: 'success',
          },
          query: {
            ticketId,
          },
        });
      }
    } catch (e: any) {
      const { code, data, message } = e;
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;

        InfoBox({
          title: t('是否继续提交单据'),
          content: () => {
            const route = router.resolve({
              name: 'bizTicketManage',
              params: {
                ticketId: id,
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
              await run({
                ...params,
                ignore_duplication: true,
              });
            } catch (e: any) {
              messageError(e?.message);
            }
          },
        });
      } else {
        messageError(message);
      }
    } finally {
      loading.value = false;
    }
  };

  return {
    run,
    loading,
  };
}
