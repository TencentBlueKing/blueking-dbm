import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { getTickets } from '@services/source/ticket';

export default (params: ServiceParameters<typeof getTickets>) => {
  const router = useRouter();

  const isChecking = ref(true);
  if (params.id) {
    getTickets(params)
      .then((data) => {
        if (data.results.length > 0) {
          return;
        }

        router.replace({
          params: {
            ticketId: '',
          },
        });
      })
      .finally(() => {
        setTimeout(() => {
          isChecking.value = false;
        }, 100);
      });
  } else {
    setTimeout(() => {
      isChecking.value = false;
    }, 100);
  }

  return isChecking;
};
