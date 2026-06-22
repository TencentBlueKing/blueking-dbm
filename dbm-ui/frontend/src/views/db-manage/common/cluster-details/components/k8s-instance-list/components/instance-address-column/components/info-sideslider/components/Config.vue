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
  <div class="k8s-instance-column-sideslider-config">
    <BkLoading
      :loading="loading"
      style="height: 100%">
      <div
        ref="editorRef"
        class="mt-8"
        :style="{ height: `${height}px` }" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import { useRequest } from 'vue-request';

  import { retrieveQdrantHaInstanceDetail } from '@services/source/qdrantHa';
  import { retrieveSurrealdbHaInstanceDetail } from '@services/source/surrealdbHa';
  import { retrieveSurrealdbSingleInstanceDetail } from '@services/source/surrealdbSingle';

  import { getOffset } from '@utils';

  import { ClusterTypes } from '@/common/const';

  interface Props {
    clusterData: {
      cluster_name: string;
      k8s_cluster_name: string;
      namespace: string;
    };
    clusterType: keyof typeof k8sApiMap;
    podName: string;
    role: string;
  }

  const props = defineProps<Props>();

  const k8sApiMap = {
    [ClusterTypes.K8S_QDRANT_HA]: retrieveQdrantHaInstanceDetail,
    [ClusterTypes.K8S_SURREALDB_HA]: retrieveSurrealdbHaInstanceDetail,
    [ClusterTypes.K8S_SURREALDB_SINGLE]: retrieveSurrealdbSingleInstanceDetail,
  };
  let editor: monaco.editor.IStandaloneCodeEditor;

  const editorRef = ref();
  const height = ref(500);

  const { loading, run: runRetriveDetail } = useRequest(k8sApiMap[props.clusterType], {
    manual: true,
    onSuccess(detailData) {
      editor.setValue(detailData.manifest);
      height.value = window.innerHeight - getOffset(editorRef.value as HTMLElement).top - 24;
    },
  });

  onMounted(() => {
    height.value = window.innerHeight - getOffset(editorRef.value as HTMLElement).top - 24;

    runRetriveDetail({
      clusterName: props.clusterData.cluster_name,
      componentName: props.role,
      k8sClusterName: props.clusterData.k8s_cluster_name,
      namespace: props.clusterData.namespace,
      podName: props.podName,
    });

    nextTick(() => {
      editor = monaco.editor.create(editorRef.value, {
        automaticLayout: true,
        language: 'yaml',
        minimap: {
          enabled: false,
        },
        padding: {
          bottom: 20, // 底部内边距（像素）
          top: 20, // 顶部内边距（像素）
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
</script>

<style lang="less">
  .k8s-instance-column-sideslider-config {
    .step-box {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
