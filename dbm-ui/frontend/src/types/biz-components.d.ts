declare module 'vue' {
  interface GlobalComponents {
    AuthButton: typeof import('@components/auth-component/button.vue').default;
    AuthTemplate: typeof import('@components/auth-component/component.vue').default;
    AuthOption: typeof import('@components/auth-component/option.vue').default;
    AuthRouterLink: typeof import('@components/auth-component/router-link.vue').default;
    AuthSwitch: typeof import('@components/auth-component/switch.vue').default;
    DbCard: typeof import('@components/db-card/index.vue').default;
    DbForm: typeof import('@components/db-form/index.vue').default;
    DbIcon: typeof import('@components/db-icon/index.ts').default;
    DbPopconfirm: typeof import('@components/db-popconfirm/index.vue').default;
    DbSearchSelect: typeof import('@components/db-search-select/index.vue').default;
    DbSideslider: typeof import('@components/db-sideslider/index.vue').default;
    DbStatus: typeof import('@components/db-status/index.vue').default;
    DbTable: typeof import('@components/db-table/index.vue').default;
    FunController: typeof import('@components/function-controller/FunController.vue').default;
    MoreActionExtend: typeof import('@components/more-action-extend/Index.vue').default;
    ScrollFaker: typeof import('@components/scroll-faker/Index.vue').default;
    SmartAction: typeof import('@components/smart-action/Index.vue').default;
    DbAppSelect: typeof import('@components/db-app-select/Index.vue').default;
  }
}

export {};
