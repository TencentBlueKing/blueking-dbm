<template>
  <div class="input-output-main">
    <div class="main-title">{{ t('输入参数') }}</div>
    <ParamEditor
      class="mb-24"
      :data="inputParam"
      :title="t('输入参数')" />
    <div class="main-title">{{ t('输出参数') }}</div>
    <ParamEditor
      :data="outputParam"
      :title="t('输出参数')" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getNodeExecutionData } from '@services/source/taskflow';

  import ParamEditor from './components/ParamEditor.vue';

  interface Props {
    nodeId?: string;
    rootId: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    nodeId: '',
  });

  const { t } = useI18n();

  const inputParam = ref('');
  const outputParam = ref('');

  const { run: runGetNodeExecutionData } = useRequest(getNodeExecutionData, {
    manual: true,
    onSuccess: (data) => {
      inputParam.value = JSON.stringify(data.inputs, null, 2);
      outputParam.value = JSON.stringify(data.outputs, null, 2);
    },
  });

  watch(
    () => props.nodeId,
    () => {
      if (props.nodeId) {
        runGetNodeExecutionData({
          node_id: props.nodeId,
          root_id: props.rootId,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .input-output-main {
    margin: 0 16px 16px;

    .main-title {
      margin-bottom: 8px;
      font-size: 14px;
      font-weight: 700;
      color: #313238;
    }
  }
</style>
