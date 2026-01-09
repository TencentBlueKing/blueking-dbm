import { Message } from 'bkui-vue';
import InfoBox from 'bkui-vue/lib/info-box';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { createTicketNew } from '@services/source/ticket';

import { useEventBus } from '@hooks';

import { type TicketTypes } from '@common/const';

import { messageError } from '@utils';

interface IRowError {
  errors: string;
  field: string;
  row_key: string;
}

export function useCreateTicket<T>(
  ticketType: TicketTypes,
  options?: {
    onError?: (errors: { errors: string; field: string; row_key: string }[]) => void;
    onSuccess?: (ticketId: number) => void;
  },
) {
  const loading = ref(false);
  const router = useRouter();
  const eventBus = useEventBus();
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

      window.changeConfirm = false;

      const route = router.resolve({
        name: 'bizTicketManage',
        params: {
          ticketId,
        },
      });

      Message({
        delay: 6000,
        dismissable: false,
        message: h('div', { style: 'width: 100%; display: flex; justify-content: space-between;' }, [
          h('span', {}, t('单据提交成功！您可以继续提交新单据')),
          h(
            'a',
            {
              href: route.href,
              target: '_blank',
            },
            t('查看详情'),
          ),
        ]),
        theme: 'success',
      });

      eventBus.emit('db-toolbox-success');

      if (options?.onSuccess) {
        options?.onSuccess(ticketId);
      }
    } catch (error: unknown) {
      const {
        code,
        data,
        errors: errorList,
        message,
      } = error as {
        code: number;
        data: {
          duplicate_ticket_id: number;
        };
        errors?: IRowError[] | string[];
        message: string;
      };
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;
        eventBus.emit('db-toolbox-error');

        setTimeout(() => {
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
        });
      } else if (errorList && errorList.length > 0) {
        if (typeof errorList[0] === 'string') {
          eventBus.emit('db-toolbox-error', errorList.join('\n'));
        } else if (options?.onError) {
          options.onError(errorList as IRowError[]);
        } else {
          eventBus.emit('db-toolbox-error', (errorList as IRowError[]).map((item) => item.errors).join(','));
        }
      } else {
        eventBus.emit('db-toolbox-error', message);
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
