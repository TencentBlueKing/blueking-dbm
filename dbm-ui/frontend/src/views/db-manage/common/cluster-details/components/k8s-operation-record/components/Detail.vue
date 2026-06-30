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
    render-directive="if"
    :title="t('操作明细')"
    :width="1100">
    <div class="k8s-operation-record-sideslider">
      <div class="info-box mt-4">
        <div class="info-item">
          <span class="info-label">{{ t('操作类型') }}：</span>
          <span>{{ data.requestType }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('操作对象') }}：</span>
          <span>{{ data.clusterName }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('关联单据') }}：</span>
          <template v-if="data?.ticketId">
            <TicketStatusTag
              :data="{
                status: data.ticket_status as TicketModel['status'],
                statusText: TicketModel.statusTextMap[data.ticket_status as TicketModel['status']],
              }" />
            <RouterLink
              class="ml-4"
              target="_blank"
              :to="{
                name: 'bizTicketManage',
                params: {
                  ticketId: data.ticketId,
                },
              }">
              {{ data.ticket_type_display }}[{{ data.ticketId }}]
            </RouterLink>
          </template>
          <span v-else> -- </span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('操作人') }}：</span>
          <span>{{ data.createdBy }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('操作时间') }}：</span>
          <span>{{ data.createdAtDisplay }}</span>
        </div>
      </div>
      <div
        ref="editorRef"
        class="mt-16"
        style="height: 500px" />
    </div>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import * as monaco from 'monaco-editor';
  import { useI18n } from 'vue-i18n';

  import KubernetesOperationLogModel from '@services/model/kubernetes/kubernetes-operation-log';
  import TicketModel from '@services/model/ticket/ticket';

  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { formatJSON } from '@utils';

  interface Props {
    data: KubernetesOperationLogModel;
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();

  const editorRef = ref();

  let editor: monaco.editor.IStandaloneCodeEditor;

  watch(
    () => props.data.id,
    () => {
      if (props.data.id) {
        editor.setValue(formatJSON(props.data.requestParams));
      }
    },
  );

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

      editor.setValue(formatJSON(props.data.requestParams));
    });
  });

  onBeforeUnmount(() => {
    editor.dispose();
  });
</script>

<style lang="less">
  .k8s-operation-record-sideslider {
    height: 100%;
    padding: 16px 24px;

    .info-box {
      display: flex;
      padding: 8px 24px;
      align-items: flex-start;
      background-color: #f5f7fa;
      flex-wrap: wrap;
      border-radius: 2px;

      .info-item {
        display: flex;
        height: 32px;
        font-size: 12px;
        flex: 0 0 33%;
        align-items: center;

        .info-label {
          color: #4d4f56;
        }
      }
    }
  }
</style>
