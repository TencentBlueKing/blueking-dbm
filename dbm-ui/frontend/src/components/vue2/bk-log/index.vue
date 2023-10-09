<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="wrapperRef"
    class="bk-log" />
</template>

<script lang="tsx">
  import { beforeLoad, loadInstance, mount, unmount } from '@blueking/bk-weweb';

  export default {
    name: 'BkLog',
  };
</script>

<script setup lang="tsx">
  interface Props {
    appKey?: string
  }

  const props = withDefaults(defineProps<Props>(), {
    appKey: 'bk-log',
  });

  const wrapperRef = ref<HTMLDivElement>();
  const vueInstance = ref();
  const bkLogInstance = ref();
  const state = reactive({
    isBefore: false,
    data: [] as any[],
  });

  /**
   * clear log
   */
  const handleLogClear = () => {
    bkLogInstance.value?.changeExecute?.();
  };

  /**
   * add log
   */
  const handleLogAdd = (data: any[] = []) => {
    // 如果在实例挂在前调用了此方法，则会在实例挂在成功后自动调用
    if (data.length > 0 && !bkLogInstance.value) {
      state.isBefore = true;
      state.data = data;
      return;
    }

    bkLogInstance.value?.addLogData?.(data);
  };

  watch(bkLogInstance, () => {
    if (bkLogInstance.value && state.isBefore) {
      handleLogAdd(state.data);
      state.isBefore = false;
      state.data = [];
    }
  });

  defineExpose({
    handleLogClear,
    handleLogAdd,
  });

  beforeLoad();
  onMounted(async () => {
    const { VITE_PUBLIC_PATH } = window.PROJECT_ENV;
    await loadInstance({
      url: `${window.location.origin}${VITE_PUBLIC_PATH ? VITE_PUBLIC_PATH : '/'}vue2-components/bk-log/index.js`,
      mode: 'js',
      id: props.appKey,
      container: wrapperRef.value,
      showSourceCode: true,
      scopeCss: true,
      scopeJs: true,
    });

    mount(props.appKey, wrapperRef.value, (instance, { Vue2, Log }: any) => {
      const div = document.createElement('div');
      wrapperRef.value?.appendChild(div);
      vueInstance.value = new Vue2({
        el: div,
        components: {
          BkLog: Log.bkLog,
        },
        data() {
          return {};
        },
        render(h: any) {
          return h('BkLog', {
            props: {
              ...props,
            },
            ref: 'bkLog',
          });
        },
      });
      bkLogInstance.value = vueInstance.value.$refs.bkLog;
    });
  });

  onBeforeUnmount(() => {
    unmount(props.appKey);
  });
</script>

<style lang="less">
  @import "./index.less";
</style>
