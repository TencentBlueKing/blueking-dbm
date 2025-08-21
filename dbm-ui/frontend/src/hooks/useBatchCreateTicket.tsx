import InfoBox from 'bkui-vue/lib/info-box';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { createTicketBatch } from '@services/source/ticket';

import type { TicketTypes } from '@common/const';

import { messageError } from '@utils';

export function useBatchCreateTicket<T>(ticketType: TicketTypes) {
  const loading = ref(false);
  const router = useRouter();
  const route = useRoute();
  const { locale, t } = useI18n();

  const doRequest = async (tickets: ServiceParameters<typeof createTicketBatch>['tickets']) => {
    try {
      loading.value = true;
      const res = await createTicketBatch({ tickets });
      const toolboxResultMap = {
        MONGODB: 'DbaManageMongodbToolboxResult',
        MYSQL: 'DbaManageMysqlToolboxResult',
        REDIS: 'DbaManageRedisToolboxResult',
        SQLSERVER: 'DbaManageSqlserverToolboxResult',
        TENDBCLUSTER: 'DbaManageTendbClusterToolboxResult',
      };
      const targetTicketType = route.meta.routeName as string;
      const [targetDb] = targetTicketType.split('_');
      const resultRouteName = toolboxResultMap[targetDb as keyof typeof toolboxResultMap];
      if (resultRouteName) {
        router.push({
          name: resultRouteName,
          params: {
            ticketIds: res.map((item) => item.id).join(','),
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
              const ignoreTickets = tickets.map((ticket) => ({
                ...ticket,
                ignore_duplication: true,
              }));
              await doRequest(ignoreTickets);
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

  const run = <U,>({
    bizIdExtractor,
    data = [],
    detailsExtractor,
    ticketPayload = {
      remark: '',
    },
  }: {
    /**
     * 指定获取业务id的方法
     */
    bizIdExtractor: (item: U) => number;
    data: U[];
    /**
     * 转成提单的details
     */
    detailsExtractor: (item: U) => T;
    ticketPayload: { remark: string };
  }) => {
    const grouped = data.reduce(
      (acc, item) => {
        const bizId = bizIdExtractor(item);
        const details = detailsExtractor(item);
        if (!acc[bizId]) {
          Object.assign(acc, { [bizId]: { bk_biz_id: bizId, details: {} } });
        }
        for (const key in details) {
          if (!acc[bizId].details[key]) {
            Object.assign(acc[bizId].details, { [key]: Array.isArray(details[key]) ? [] : details[key] });
          }
          if (Array.isArray(details[key])) {
            acc[bizId].details[key].push(...details[key]);
          }
        }
        return acc;
      },
      {} as Record<number, { bk_biz_id: number; details: { [key: string]: any } }>,
    );

    const ticketParams = Object.values(grouped).map((item) => ({
      ...item,
      ...ticketPayload,
      ticket_type: ticketType,
    }));

    doRequest(ticketParams);
  };

  return {
    loading,
    run,
  };
}
