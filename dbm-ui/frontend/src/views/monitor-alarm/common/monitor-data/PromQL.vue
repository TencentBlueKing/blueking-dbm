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
  <div class="monitor-data-promql">
    <BkAlert :title="t('PromQL 表达式由平台预置，不可修改。')" />
    <div
      ref="editorRef"
      class="mt-8"
      style="height: 100px" />
    <div class="step-box mt-8">
      <span class="mr-4">Step</span>
      <!-- <DbIcon
        v-bk-tooltips="t('数据步长')"
        class="mr-4"
        style="font-size: 14px"
        type="attention" /> -->
      <BkInput
        v-model="step"
        :min="1"
        style="width: 100px"
        type="number">
      </BkInput>
      <span class="ml-4">{{ t('秒') }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import { promLanguageDefinition } from 'monaco-promql';
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  interface Props {
    data: MonitorPolicyModel['agg_info'];
  }

  interface Exposes {
    getValue: () => Props['data'];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const editorRef = ref();
  const step = ref(0);

  let editor: monaco.editor.IStandaloneCodeEditor;

  watch(
    () => props.data,
    () => {
      step.value = props.data[0].agg_interval;
      setTimeout(() => {
        editor.setValue(props.data[0].promql || '');
      });
    },
    {
      immediate: true,
    },
  );

  onMounted(() => {
    monaco.languages.register({ id: 'promql' });

    promLanguageDefinition.loader().then((promqlModule) => {
      if (promqlModule.language) {
        monaco.languages.setMonarchTokensProvider('promql', promqlModule.language);
      }
    });

    nextTick(() => {
      editor = monaco.editor.create(editorRef.value, {
        automaticLayout: true,
        language: 'promql',
        minimap: {
          enabled: false,
        },
        readOnly: true,
        renderLineHighlight: 'none',
        scrollbar: {
          alwaysConsumeMouseWheel: false,
        },
        theme: 'vs-dark',
        wordWrap: 'on',
      });
    });
  });

  onBeforeUnmount(() => {
    editor.dispose();
  });

  defineExpose<Exposes>({
    getValue() {
      const promqlData = { ...props.data[0] };
      return [Object.assign(promqlData, { agg_interval: step.value })];
    },
  });
</script>

<style lang="less">
  .monitor-data-promql {
    .step-box {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
