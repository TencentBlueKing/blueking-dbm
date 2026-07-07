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
  <BkSideslider
    v-model:is-show="isShow"
    :title="t('配置变更')"
    :width="1100">
    <div class="k8s-instance-list-patch-config">
      <BkLoading :loading="isGetConfigLoading">
        <div class="config-header">[{{ role }}] {{ t('当前配置信息') }}</div>
        <div
          ref="editorRef"
          style="height: 500px" />
      </BkLoading>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="isLoading"
        :loading="isLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        :disabled="isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import * as monaco from 'monaco-editor';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getComponentConfig, patchComponentConfig } from '@services/source/kubernetesToolbox';

  import { useUserProfile } from '@stores';

  import { objectToJSON } from '@utils';

  interface Props {
    clusterData: {
      cluster_name: string;
      k8s_cluster_name: string;
      namespace: string;
    };
    role: string;
  }

  interface Emits {
    (e: 'success'): void;
    (e: 'cancel'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const userProfile = useUserProfile();

  const editorRef = ref();

  let editor: monaco.editor.IStandaloneCodeEditor;

  const isLoading = computed(() => isGetConfigLoading.value || isPatchConfigLoading.value);

  const { loading: isGetConfigLoading, run: runGetComponentConfig } = useRequest(getComponentConfig, {
    manual: true,
    onSuccess(configData) {
      editor.setValue(objectToJSON(configData.config));
    },
  });

  const { loading: isPatchConfigLoading, run: runPatchComponentConfig } = useRequest(patchComponentConfig, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      emits('success');
    },
  });

  const handleConfirm = () => {
    const config = JSON.parse(editor.getValue());

    runPatchComponentConfig({
      bk_username: userProfile.username,
      clusterName: props.clusterData.cluster_name,
      componentList: [
        {
          componentName: props.role,
          config,
        },
      ],
      k8sClusterName: props.clusterData.k8s_cluster_name,
      namespace: props.clusterData.namespace,
    });
  };

  const handleClose = () => {
    isShow.value = false;
  };

  onMounted(() => {
    nextTick(() => {
      editor = monaco.editor.create(editorRef.value, {
        automaticLayout: true,
        language: 'json',
        minimap: {
          enabled: false,
        },
        padding: {
          bottom: 20, // 底部内边距（像素）
          top: 20, // 顶部内边距（像素）
        },
        renderLineHighlight: 'none',
        scrollbar: {
          alwaysConsumeMouseWheel: false,
        },
        theme: 'vs-dark',
        wordWrap: 'on',
      });

      runGetComponentConfig({
        bk_username: userProfile.username,
        clusterName: props.clusterData.cluster_name,
        componentName: props.role,
        k8sClusterName: props.clusterData.k8s_cluster_name,
        namespace: props.clusterData.namespace,
      });
    });
  });

  onBeforeUnmount(() => {
    editor.dispose();
  });
</script>

<style lang="less">
  .k8s-instance-list-patch-config {
    display: flex;
    width: 100%;
    padding: 24px 24px 0;
    flex-direction: column;

    .config-header {
      height: 40px;
      padding-left: 24px;
      line-height: 40px;
      color: #c4c6cc;
      background-color: #242424;
    }
  }
</style>
