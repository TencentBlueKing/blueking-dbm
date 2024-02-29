declare module 'vue' {
  interface GlobalComponents {
    FunController: typeof import('../components/function-controller/FunController.vue').default;
    AuthButton: typeof import('../components/auth-component/button.vue').default;
    AuthOption: typeof import('../components/auth-component/option.vue').default;
    AuthRouterLink: typeof import('../components/auth-component/router-link.vue').default;
    AuthSwitch: typeof import('../components/auth-component/switch.vue').default;
  }
}

export {};
