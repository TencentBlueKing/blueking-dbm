import { registerBusinessModule, registerModule } from '@router';

import { t } from '@locales/index';

export default () => {
  registerModule([
    {
      name: 'SelfServiceMyTickets',
      path: 'ticket-self-apply/:typeId?',
      meta: {
        navName: t('我的申请'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-apply/Index.vue'),
    },
    {
      name: 'ticketSelfManage',
      path: 'ticket-self-manage',
      meta: {
        navName: t('我负责的业务'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-manage/Index.vue'),
    },
    {
      name: 'MyTodos',
      path: 'ticket-self-todo/:status?',
      meta: {
        navName: t('我的待办'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-todo/Index.vue'),
    },
    {
      name: 'ticketSelfDone',
      path: 'ticket-self-done',
      meta: {
        navName: t('我的已办'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-done/Index.vue'),
    },
  ]);

  registerBusinessModule([
    {
      name: 'bizTicketManage',
      path: 'ticket-manage',
      meta: {
        navName: t('单据'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/business/Index.vue'),
    },
  ]);
};
