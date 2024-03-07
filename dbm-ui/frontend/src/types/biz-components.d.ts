declare module 'vue' {
  interface GlobalComponents {
    FunController: typeof import('../components/function-controller/FunController.vue').default;
    AuthButton: typeof import('../components/auth-component/button.vue').default;
    AuthOption: typeof import('../components/auth-component/option.vue').default;
    AuthRouterLink: typeof import('../components/auth-component/router-link.vue').default;
    AuthSwitch: typeof import('../components/auth-component/switch.vue').default;
    AuthTemplate: typeof import('../components/auth-component/component.vue').default;
    SmartAction: typeof import('../components/smart-action/Index.vue').default;
    DbIcon: typeof import('../components/db-icon/index.ts').default;
    DbForm: typeof import('../components/db-form/index.vue').default;
    DbAppSelect: typeof import('../components/db-app-select/Index.vue').default;
    DbPopconfirm: typeof import('../components/db-popconfirm/index.vue').default;
    ScrollFaker: typeof import('../components/scroll-faker/Index.vue').default;
  }
}

export {};
