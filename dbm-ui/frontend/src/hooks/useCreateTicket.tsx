import { Message } from 'bkui-vue';
import InfoBox from 'bkui-vue/lib/info-box';
import { type Ref } from 'vue';
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

interface CreateTicketOptions {
  /**
   * 是否工具箱提单场景，默认 true：成功/失败经 eventBus 通知工具箱页（重置表单、内联展示错误）
   * 非工具箱场景传 false：失败时用 messageError 全局提示
   */
  isToolbox?: boolean;
  onError?: (errors: { errors: string; field: string; row_key: string }[]) => void;
  onSuccess?: (ticketId: number) => void;
  /**
   * 成功提示文案，默认「单据提交成功！您可以继续提交新单据」
   * 传 false 不弹成功提示（成功动作由 onSuccess 自行处理）
   */
  successMessage?: string | false;
}

interface RunFormDataBase<T> {
  /** 默认当前业务 window.PROJECT_CONFIG.BIZ_ID */
  bk_biz_id?: number;
  details: T;
  ignore_duplication?: boolean;
  remark?: string;
}

interface CreateTicketReturn<T, RequireTicketType extends boolean> {
  loading: Ref<boolean>;
  /**
   * 创建单据
   * @returns 成功返回单据 id；失败（含重复单据确认分流）返回 undefined
   */
  run(
    formData: (RequireTicketType extends true
      ? {
          /** 创建 hook 时未传 ticketType，此处必传 */
          ticket_type: TicketTypes;
        }
      : {
          /** 默认创建 hook 时传入的 ticketType */
          ticket_type?: TicketTypes;
        }) &
      RunFormDataBase<T>,
  ): Promise<number | undefined>;
}

// 创建时传入 ticketType：run 的 ticket_type 可选，默认取创建时的值
export function useCreateTicket<T>(
  ticketType: TicketTypes,
  options?: CreateTicketOptions,
): CreateTicketReturn<T, false>;
// 创建时未传 ticketType：run 必须传 ticket_type
export function useCreateTicket<T>(ticketType?: undefined, options?: CreateTicketOptions): CreateTicketReturn<T, true>;
// 实现签名对调用方不可见；返回类型取两个重载的联合以兼容二者
export function useCreateTicket<T>(
  ticketType?: TicketTypes,
  options?: CreateTicketOptions,
): CreateTicketReturn<T, false> | CreateTicketReturn<T, true> {
  const loading = ref(false);
  const router = useRouter();
  const eventBus = useEventBus();
  const { locale, t } = useI18n();

  const isToolbox = options?.isToolbox ?? true;

  // 失败提示：工具箱场景经 eventBus 由页面内联展示，其他场景全局提示
  const showError = (errorMessage?: string) => {
    eventBus.emit('db-toolbox-error', errorMessage);
    if (!isToolbox && errorMessage) {
      messageError(errorMessage);
    }
  };

  const run = async (
    formData: {
      /** 默认创建 hook 时传入的 ticketType */
      ticket_type?: TicketTypes;
    } & RunFormDataBase<T>,
  ): Promise<number | undefined> => {
    const finalTicketType = formData.ticket_type ?? ticketType;
    if (!finalTicketType) {
      throw new Error('useCreateTicket: 缺少 ticket_type，请在创建 hook 或调用 run 时传入');
    }
    const params = {
      bk_biz_id: formData.bk_biz_id ?? window.PROJECT_CONFIG.BIZ_ID,
      details: formData.details,
      ignore_duplication: formData.ignore_duplication,
      remark: formData.remark || '',
      ticket_type: finalTicketType,
    };
    try {
      loading.value = true;
      const { id: ticketId } = await createTicketNew<T>(params);

      window.changeConfirm = false;

      if (options?.successMessage !== false) {
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
            h('span', {}, options?.successMessage || t('单据提交成功！您可以继续提交新单据')),
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
      }

      eventBus.emit('db-toolbox-success');

      if (options?.onSuccess) {
        options?.onSuccess(ticketId);
      }

      return ticketId;
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
        showError();

        // 重复单据：返回挂起的 Promise，待用户在确认弹窗中操作后再落定，与调用方 await 语义对齐
        return new Promise<number | undefined>((resolve) => {
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
              onCancel: () => {
                resolve(undefined);
              },
              onConfirm: async () => {
                try {
                  const retryTicketId = await run({
                    ...params,
                    ignore_duplication: true,
                  });
                  resolve(retryTicketId);
                } catch (e: any) {
                  messageError(e?.message);
                  resolve(undefined);
                }
              },
              title: t('是否继续提交单据'),
            });
          });
        });
      } else if (errorList && errorList.length > 0) {
        if (typeof errorList[0] === 'string') {
          showError(errorList.join('\n'));
        } else if (options?.onError) {
          options.onError(errorList as IRowError[]);
        } else {
          showError((errorList as IRowError[]).map((item) => item.errors).join(','));
        }
      } else {
        showError(message);
      }

      return undefined;
    } finally {
      loading.value = false;
    }
  };

  return {
    loading,
    run,
  };
}
