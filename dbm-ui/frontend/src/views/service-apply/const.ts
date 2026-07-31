import type { InjectionKey } from 'vue';

export const serviceApplyKey: InjectionKey<{ changeBizId: (id: number) => void }> = Symbol('serviceApply');
