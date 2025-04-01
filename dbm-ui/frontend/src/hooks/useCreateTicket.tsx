import InfoBox from 'bkui-vue/lib/info-box';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { createTicketNew } from '@services/source/ticket';

import { DBTypeInfos, type TicketTypes } from '@common/const';

import { messageError } from '@utils';

export function useCreateTicket<T>(
  ticketType: TicketTypes,
  options?: { onSuccess?: (ticketId: number) => void; ticketTypeRoute?: TicketTypes },
) {
  const loading = ref(false);
  const router = useRouter();
  const route = useRoute();
  const { locale, t } = useI18n();

  const run = async (formData: { details: T; ignore_duplication?: boolean; remark?: string }) => {
    const params = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details: formData.details,
      ignore_duplication: formData.ignore_duplication,
      remark: formData.remark || '',
      ticket_type: ticketType,
    };
    try {
      loading.value = true;
      const { id: ticketId } = await createTicketNew<T>(params);
      if (options?.onSuccess) {
        options.onSuccess(ticketId);
      } else if (options?.ticketTypeRoute || route.name === ticketType) {
        const targetTicketType = options?.ticketTypeRoute || ticketType;
        const targetDb = targetTicketType.split('_')[0];
        if (Object.keys(DBTypeInfos).includes(targetDb.toLocaleLowerCase())) {
          router.push({
            name: `${targetDb}_ToolboxResult`,
            params: {
              ticketId,
              ticketType: targetTicketType,
            },
          });
        }
      }
    } catch (e: any) {
      const { code, data, message } = e;
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;

        InfoBox({
          cancelText: t('取消提单'),
          confirmText: t('继续提单'),
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
          title: t('是否继续提交单据'),
        });
      } else {
        messageError(message);
      }
    } finally {
      loading.value = false;
    }
  };

  return {
    loading,
    run,
  };
}
