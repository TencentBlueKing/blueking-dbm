declare module 'vue' {
  interface GlobalComponents {
    FunController: typeof import('../components/function-controller/FunController.vue').default
  }
}

export {};
