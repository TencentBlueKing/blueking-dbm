import { createTicket } from '@services/source/ticket';

import type { TicketTypes } from '@common/const';

export function useCreateTicket<T>(ticketType: TicketTypes) {
  const loading = ref(false);
  const router = useRouter();

  const run = async (details: T, remark = '') => {
    loading.value = true;
    const { id } = await createTicket<T>({
      ticket_type: ticketType,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details,
      remark,
      ignore_duplication: true,
    });
    loading.value = false;
    router.push({
      name: ticketType,
      params: {
        page: 'success',
      },
      query: {
        ticketId: id,
      },
    });
  };

  return {
    run,
    loading,
  };
}
