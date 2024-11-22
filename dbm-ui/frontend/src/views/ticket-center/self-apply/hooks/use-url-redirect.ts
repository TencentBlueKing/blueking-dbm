import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { getTicketDetails } from '@services/source/ticket';

import { useUserProfile } from '@stores';

export default (ticketId?: number) => {
  const router = useRouter();
  const route = useRoute();
  const { username } = useUserProfile();

  const isLoading = ref(false);

  if (ticketId) {
    isLoading.value = true;
    getTicketDetails({
      id: ticketId,
    })
      .then((data) => {
        if (data.creator === username) {
          return;
        }
        if (data.isTodo) {
          if (route.name !== 'MyTodos') {
            router.replace({
              name: 'MyTodos',
              params: {
                status: data.status,
                ticketId,
              },
              query: {
                id: ticketId,
              },
            });
          }
        }
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  return {
    loading: isLoading,
  };
};
