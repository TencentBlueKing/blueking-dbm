import { registerBusinessModule, registerModule } from '@router';

import { t } from '@locales/index';

export default () => {
  registerModule([
    {
      name: 'SelfServiceMyTickets',
      path: 'ticket-self-apply/:ticketId?',
      meta: {
        navName: t('我的申请'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-apply/Index.vue'),
    },
    {
      name: 'MyTodos',
      path: 'ticket-self-todo/:assist?/:status?/:ticketId?',
      meta: {
        navName: t('我的待办'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-todo/Index.vue'),
      beforeEnter: (to, from, next) => {
        if (!to.params.assist) {
          // 设置默认值
          Object.assign(to.params, {
            assist: '0',
          });
        }
        next();
      },
    },
    {
      name: 'ticketSelfDone',
      path: 'ticket-self-done/:ticketId?',
      meta: {
        navName: t('我的已办'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-done/Index.vue'),
    },
    {
      name: 'ticketSelfManage',
      path: 'ticket-self-manage/:ticketId?',
      meta: {
        navName: t('我负责的业务'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/self-manage/Index.vue'),
    },
    {
      name: 'ticketPlatformManage',
      path: 'ticket-platform-manage/:ticketId?',
      meta: {
        navName: t('单据'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/platform-manage/Index.vue'),
    },
    {
      name: 'ticketDetail',
      path: 'ticket/:ticketId?',
      meta: {
        navName: t('单据详情'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/detail-page/Index.vue'),
    },
  ]);

  registerBusinessModule([
    {
      name: 'bizTicketManage',
      path: 'ticket-manage/:ticketId?',
      meta: {
        navName: t('单据'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-center/business/Index.vue'),
    },
  ]);
};
