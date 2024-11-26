import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { getTickets } from '@services/source/ticket';

import { messageWarn } from '@utils';

export default (params: ServiceParameters<typeof getTickets>) => {
  const router = useRouter();
  const route = useRoute();

  const { t } = useI18n();

  const isChecking = ref(true);
  if (params.id) {
    getTickets(params)
      .then((data) => {
        if (data.results.length > 0) {
          return;
        }
        messageWarn(
          t('单据t不在n单据中', {
            t: params.id,
            n: route.meta.navName,
          }),
          5000,
        );

        router.replace({
          params: {
            ticketId: '',
          },
        });
      })
      .finally(() => {
        setTimeout(() => {
          isChecking.value = false;
        });
      });
  } else {
    setTimeout(() => {
      isChecking.value = false;
    });
  }

  return isChecking;
};
