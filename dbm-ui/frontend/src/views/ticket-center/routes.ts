import { registerBusinessModule, registerModule } from '@router';

import { t } from '@locales/index';

export default () => {
  registerModule([
    {
      path: 'ticket-self-apply/:ticketId?',
      name: 'SelfServiceMyTickets',
      meta: {
        fullscreen: true,
        navName: t('我的申请'),
      },
      component: () => import('@views/ticket-center/ticket-self-apply/Index.vue'),
    },
    {
      path: 'ticket-self-todo/:assist?/:status?/:ticketId?',
      name: 'MyTodos',
      meta: {
        fullscreen: true,
        navName: t('我的待办'),
      },
      beforeEnter: (to, from, next) => {
        if (!to.params.assist) {
          // 设置默认值
          Object.assign(to.params, {
            assist: '0',
          });
        }
        next();
      },
      component: () => import('@views/ticket-center/ticket-self-todo/Index.vue'),
    },
    {
      path: 'ticket-self-done/:ticketId?',
      name: 'ticketSelfDone',
      meta: {
        fullscreen: true,
        navName: t('我的已办'),
      },
      component: () => import('@views/ticket-center/ticket-self-done/Index.vue'),
    },
    // {
    //   path: 'ticket-self-manage/:ticketId?',
    //   name: 'ticketSelfManage',
    //   meta: {
    //     fullscreen: true,
    //     navName: t('我负责的业务'),
    //   },
    //   component: () => import('@views/ticket-center/ticket-self-manage/Index.vue'),
    // },
    {
      path: 'ticket-platform-manage/:ticketId?',
      name: 'ticketPlatformManage',
      meta: {
        fullscreen: true,
        navName: t('单据'),
      },
      component: () => import('@views/ticket-center/ticket-platform-manage/Index.vue'),
    },
    {
      path: 'ticket/:ticketId?',
      name: 'ticketDetail',
      meta: {
        fullscreen: true,
        navName: t('单据详情'),
      },
      component: () => import('@views/ticket-center/detail/Index.vue'),
    },
  ]);

  registerBusinessModule([
    {
      path: 'ticket-business-manage/:ticketId?',
      name: 'bizTicketManage',
      meta: {
        fullscreen: true,
        navName: t('单据'),
      },
      component: () => import('@views/ticket-center/ticket-business-manage/Index.vue'),
    },
  ]);
};
