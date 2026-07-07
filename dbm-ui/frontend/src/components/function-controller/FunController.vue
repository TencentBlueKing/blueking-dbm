<template>
  <template v-if="showFunction">
    <slot />
  </template>
</template>

<script lang="ts">
  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  interface Props<T> {
    controllerId?: T;
    moduleId: ExtractedControllerDataKeys;
  }
</script>

<script setup lang="ts" generic="T extends FunctionKeys">
  const props = defineProps<Props<T>>();

  const funControllerStore = useFunController();

  const showFunction = computed(() => {
    const { controllerId, moduleId } = props;

    const data = funControllerStore.funControllerData[moduleId];

    if (data) {
      // 数据库组件开启且具体功能开启
      if (controllerId) {
        const children = data.children as Record<T, ControllerBaseInfo>;
        return data.is_enabled && children[controllerId]?.is_enabled;
      }

      // 只需判断数据库组件是否开启
      return data.is_enabled;
    }

    return false;
  });
</script>
