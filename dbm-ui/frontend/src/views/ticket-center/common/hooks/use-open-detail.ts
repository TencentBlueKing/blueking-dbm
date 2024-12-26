import { getCurrentInstance } from 'vue';
import { useRouter } from 'vue-router';

import TicketModel from '@services/model/ticket/ticket';

import { useStretchLayout, useUrlSearch } from '@hooks';

export default () => {
  const { splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const currentInstance = getCurrentInstance();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  return (ticketData: TicketModel, event: MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      const { href } = router.resolve({
        name: 'ticketDetail',
        params: {
          ticketId: ticketData.id,
        },
      });
      return window.open(href);
    }

    stretchLayoutSplitScreen();
    setTimeout(() => {
      if (currentInstance!.isUnmounted) {
        return;
      }
      router.replace({
        params: {
          ticketId: ticketData.id,
        },
        query: getSearchParams(),
      });
    });
  };
};
