import { registerBusinessModule, registerModule } from '@router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export default () => {
  // 注册全局模块
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

  if (checkDbConsole('globalConfigManage.ticketFlowSetting')) {
    registerModule([
      {
        path: 'ticket-flow-global-settings',
        name: 'PlatformTicketFlowSetting',
        meta: {
          fullscreen: true,
          navName: t('单据流程设置'),
        },
        component: () => import('@views/ticket-center/ticket-flow-global-settings/Index.vue'),
      },
    ]);
  }

  // 注册业务模块
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
  if (checkDbConsole('bizConfigManage.ticketCooperationSetting')) {
    registerBusinessModule([
      {
        path: 'ticket-cooperation-settings',
        name: 'TicketCooperationSetting',
        meta: {
          navName: t('单据协助设置'),
        },
        component: () => import('@views/ticket-center/ticket-cooperation-settings/Index.vue'),
      },
    ]);
  }
  if (checkDbConsole('bizConfigManage.ticketFlowSetting')) {
    registerBusinessModule([
      {
        path: 'ticket-flow-settings',
        name: 'TicketFlowSetting',
        meta: {
          fullscreen: true,
          navName: t('单据免审批设置'),
        },
        component: () => import('@views/ticket-center/ticket-flow-settings/Index.vue'),
      },
    ]);
  }
  if (checkDbConsole('bizConfigManage.ticketNoticeSetting')) {
    registerBusinessModule([
      {
        path: 'ticket-notice',
        name: 'TicketNoticeSetting',
        meta: {
          fullscreen: true,
          navName: t('单据通知'),
        },
        component: () => import('@views/ticket-center/ticket-notice/Index.vue'),
      },
    ]);
  }
};
