<template>
  <template v-if="showFunction">
    <slot />
  </template>
</template>

<script setup lang="ts" generic="T extends FunctionKeys">
  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  interface Props {
    moduleId: ExtractedControllerDataKeys,
    controllerId?: T
  }

  const props = defineProps<Props>();

  const funControllerStore = useFunController();

  const showFunction = computed(() => {
    const { moduleId, controllerId } = props;

    const data = funControllerStore.funControllerData[moduleId];

    if (data) {
      // 数据库组件开启且具体功能开启
      if (controllerId) {
        const children = data.children as Record<T, ControllerBaseInfo>;
        return data.is_enabled && children[controllerId].is_enabled;
      }

      // 只需判断数据库组件是否开启
      return data.is_enabled;
    }

    return false;
  });
</script>
