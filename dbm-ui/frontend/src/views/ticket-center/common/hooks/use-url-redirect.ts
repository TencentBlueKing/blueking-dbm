import { onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { getTicketDetails } from '@services/source/ticket';

import { useUserProfile } from '@stores';

import { getBusinessHref } from '@utils';

import { useWindowFocus } from '@vueuse/core';

const URL_QUERY_KEY = 'latest_url_record';

export default (ticketId?: number) => {
  const router = useRouter();
  const route = useRoute();
  const { username } = useUserProfile();

  const isLoading = ref(false);

  const urlRecord = localStorage.getItem(URL_QUERY_KEY);

  if (ticketId && urlRecord !== window.location.pathname) {
    isLoading.value = true;
    getTicketDetails({
      id: ticketId,
    })
      .then((data) => {
        if (data.isTodo && data.todo_operators.includes(username)) {
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
        } else if (route.name !== 'bizTicketManage') {
          const { href } = router.resolve({
            name: 'bizTicketManage',
            params: {
              status: data.status,
              ticketId,
            },
            query: {
              id: ticketId,
            },
          });

          window.location.href = getBusinessHref(href, data.bk_biz_id);
        }
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  const focused = useWindowFocus();

  watch(
    () => [focused, route],
    () => {
      localStorage.setItem(URL_QUERY_KEY, window.location.pathname);
    },
    {
      immediate: true,
      deep: true,
    },
  );

  onBeforeUnmount(() => {
    localStorage.removeItem(URL_QUERY_KEY);
  });

  return {
    loading: isLoading,
  };
};
