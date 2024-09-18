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
  <BkTimeline :list="flowTimeline">
    <template #content="{ content }">
      <FlowContent
        :content="content"
        :flows="flows"
        :ticket-data="ticketData"
        @fetch-data="handleFetchData">
        <template #extra-text>
          <template v-if="content.status === 'SUCCEEDED' && content.details.ticket_data?.dump_file_path">
            ，
            <BkButton
              class="download-button"
              text
              theme="primary"
              @click="handleDownload(`${content.details.ticket_data.dump_file_path}/`)">
              <DbIcon
                class="download-line-button"
                type="download-line" />
              <span class="ml-2">{{ t('下载结果文件') }}</span>
            </BkButton>
          </template>
        </template>
      </FlowContent>
    </template>
  </BkTimeline>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { MySQLExportData } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket'
  import { createBkrepoAccessToken } from '@services/source/storage';
  import type { FlowItem } from '@services/types/ticket';

  import FlowIcon from '@views/tickets/common/components/flow-content/components/FlowIcon.vue';
  import FlowContent from '@views/tickets/common/components/flow-content/Index.vue';

  import { downloadUrl } from '@/utils';

  interface Props {
    ticketData: TicketModel<MySQLExportData>,
    flows?: FlowItem[]
  }

  interface Emits {
    (e: 'fetch-data'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    flows: () => [],
  });
  const emits = defineEmits<Emits>()

  const { t } = useI18n();

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type === 'PAUSE' ? `${t('确认是否执行')}“${flow.flow_type_display}”` : flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    icon: () => <FlowIcon data={flow} />,
  })));

  const handleDownload = async (filePath: string) => {
    const tokenResult = await createBkrepoAccessToken({ file_path: filePath });
    const url = `${tokenResult.url}/generic/temporary/download/${tokenResult.project}/${tokenResult.repo}/${tokenResult.path}?token=${tokenResult.token}&download=true`
    downloadUrl(url)
  };

  const handleFetchData = () => {
    emits('fetch-data');
  };
</script>

<style lang="less" scoped>
  :deep(.download-button) {
    .bk-button-text {
      display: inline;
    }

    .download-line-button {
      font-size: 16px;
    }
  }
</style>
