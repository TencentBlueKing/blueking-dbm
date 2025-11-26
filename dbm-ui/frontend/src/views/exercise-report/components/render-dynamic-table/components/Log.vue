<template>
  <BkSideslider
    v-model:is-show="isShow"
    class="dynamic-log-sideslider"
    quick-close
    render-directive="if"
    :title="title"
    :width="960">
    <div class="log-content">
      <DbLog
        ref="logRef"
        :loading="initLoading" />
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import DbLog from '@components/db-log/index.vue';

  interface Props {
    log: string;
    title?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const logRef = ref<InstanceType<typeof DbLog>>();
  const initLoading = ref(false);

  watch(isShow, () => {
    if (isShow.value) {
      initLoading.value = true;
      setTimeout(() => {
        logRef.value?.init();
        setTimeout(() => {
          const logList = props.log
            .trim()
            .split('\n')
            .map((item) => {
              return {
                levelname: '',
                message: item,
                timestamp: 0,
              };
            });
          logRef.value?.setLog(logList);
          initLoading.value = false;
        });
      }, 300);
    } else {
      logRef.value!.destroy();
    }
  });
</script>
<style lang="less" scoped>
  .dynamic-log-sideslider {
    .log-content {
      height: calc(100vh - 90px);
      padding: 16px 16px 0;
    }
  }
</style>
