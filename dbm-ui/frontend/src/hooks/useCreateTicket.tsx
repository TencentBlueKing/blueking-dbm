import InfoBox from 'bkui-vue/lib/info-box';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { createTicketNew } from '@services/source/ticket';

import { type TicketTypes } from '@common/const';

import { messageError } from '@utils';

export function useCreateTicket<T>(ticketType: TicketTypes, options?: { onSuccess?: (ticketId: number) => void }) {
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
        return;
      }
      const toolboxResultMap = {
        MONGODB: 'MongodbToolboxResult',
        MYSQL: 'MysqlToolboxResult',
        ORACLE: 'OracleToolboxResult',
        REDIS: 'RedisToolboxResult',
        SQLSERVER: 'SqlserverToolboxResult',
        TENDBCLUSTER: 'TendbclusterToolboxResult',
      };
      const targetTicketType = route.meta.routeName as string;
      const targetDb = targetTicketType.split('_')[0];
      const resultRouteName = toolboxResultMap[targetDb as keyof typeof toolboxResultMap];
      if (resultRouteName) {
        router.push({
          name: resultRouteName,
          params: {
            ticketId,
            ticketType: targetTicketType,
          },
        });
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
                  The system has detected that a similar ticket has already been submitted
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
                系统检测到已提交过包含相同集群的同类
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
