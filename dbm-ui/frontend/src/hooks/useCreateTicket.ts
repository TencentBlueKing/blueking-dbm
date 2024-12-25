import { createTicket } from '@services/source/ticket';

import type { TicketTypes } from '@common/const';

export function useCreateTicket<T>(ticketType: TicketTypes, options?: { onSuccess: (ticketId: number) => void }) {
  const loading = ref(false);
  const router = useRouter();

  const run = async (details: T, remark = '') => {
    loading.value = true;
    const { id: ticketId } = await createTicket<T>({
      ticket_type: ticketType,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details,
      remark,
      ignore_duplication: true,
    });
    loading.value = false;
    if (options) {
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
  };

  return {
    run,
    loading,
  };
}
