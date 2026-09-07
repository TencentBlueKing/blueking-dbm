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
