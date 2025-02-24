import { registerBusinessModule, registerModule } from '@router';

import { t } from '@locales/index';

export default () => {
  registerModule([
    {
      component: () => import('@views/ticket-center/self-apply/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('我的申请'),
      },
      name: 'SelfServiceMyTickets',
      path: 'ticket-self-apply/:ticketId?',
    },
    {
      beforeEnter: (to, from, next) => {
        if (!to.params.assist) {
          // 设置默认值
          Object.assign(to.params, {
            assist: '0',
          });
        }
        next();
      },
      component: () => import('@views/ticket-center/self-todo/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('我的待办'),
      },
      name: 'MyTodos',
      path: 'ticket-self-todo/:assist?/:status?/:ticketId?',
    },
    {
      component: () => import('@views/ticket-center/self-done/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('我的已办'),
      },
      name: 'ticketSelfDone',
      path: 'ticket-self-done/:ticketId?',
    },
    {
      component: () => import('@views/ticket-center/self-manage/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('我负责的业务'),
      },
      name: 'ticketSelfManage',
      path: 'ticket-self-manage/:ticketId?',
    },
    {
      component: () => import('@views/ticket-center/platform-manage/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('单据'),
      },
      name: 'ticketPlatformManage',
      path: 'ticket-platform-manage/:ticketId?',
    },
    {
      component: () => import('@views/ticket-center/detail-page/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('单据详情'),
      },
      name: 'ticketDetail',
      path: 'ticket/:ticketId?',
    },
  ]);

  registerBusinessModule([
    {
      component: () => import('@views/ticket-center/business/Index.vue'),
      meta: {
        fullscreen: true,
        navName: t('单据'),
      },
      name: 'bizTicketManage',
      path: 'ticket-manage/:ticketId?',
    },
  ]);
};
