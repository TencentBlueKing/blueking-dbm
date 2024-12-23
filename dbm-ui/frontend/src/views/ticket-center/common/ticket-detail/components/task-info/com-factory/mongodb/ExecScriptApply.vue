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
  <InfoList>
    <InfoItem :label="t('脚本来源：')">
      {{ ticketDetails.details.mode === 'file' ? t('脚本文件') : t('手动输入') }}
    </InfoItem>
    <InfoItem :label="t('脚本执行内容：')">
      <BkButton
        text
        theme="primary"
        @click="handleClickFile">
        {{ t('点击查看') }}
      </BkButton>
    </InfoItem>
    <InfoItem
      :label="t('目标集群：')"
      style="flex: 1 0 100%">
      <BkTable :data="tableData">
        <BkTableColumn
          field="immute_domain"
          :label="t('集群')">
          <template #default="{data}: {data: IRowData}">
            {{ ticketDetails.details.clusters[data.id].immute_domain }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="cluster_type_name"
          :label="t('类型')">
          <template #default="{data}: {data: IRowData}">
            {{ ticketDetails.details.clusters[data.id].cluster_type_name }}
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
  </InfoList>
  <BkSideslider
    class="mongodb-exec-script-apply-content-dialog"
    :is-show="isShow"
    render-directive="if"
    :title="t('执行脚本变更_内容详情')"
    :width="960"
    :z-index="99999"
    @closed="handleClose">
    <div
      v-if="uploadFileList.length > 1"
      class="editor-layout">
      <div class="editor-layout-left">
        <RenderFileList
          v-model="selectFileName"
          :data="uploadFileList" />
      </div>
      <div class="editor-layout-right">
        <RenderFileContent
          :model-value="currentFileContent"
          readonly
          :title="selectFileName" />
      </div>
    </div>
    <template v-else>
      <RenderFileContent
        :model-value="currentFileContent"
        readonly
        :title="uploadFileList.toString()" />
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import RenderFileContent from '@views/ticket-center/common/ticket-detail/components/common/SqlFileContent.vue';
  import RenderFileList from '@views/ticket-center/common/ticket-detail/components/common/SqlFileList.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ExecScriptApply>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_EXEC_SCRIPT_APPLY,
    inheritAttrs: false,
  });

  type IRowData = { id: number };

  const tableData = props.ticketDetails.details.cluster_ids.map((item) => ({
    id: item,
  }));

  const { t } = useI18n();

  const selectFileName = ref('');
  const isShow = ref(false);

  const fileContentMap = shallowRef<Record<string, string>>({});
  const uploadFileList = shallowRef<Array<string>>([]);

  const currentFileContent = computed(() => fileContentMap.value[selectFileName.value] || '');

  // 查看日志详情
  const handleClickFile = () => {
    const { scripts } = props.ticketDetails.details;
    isShow.value = true;
    uploadFileList.value = scripts.map((item) => item.name);

    fileContentMap.value = scripts.reduce(
      (result, fileInfo) =>
        Object.assign(result, {
          [fileInfo.name]: fileInfo.content,
        }),
      {} as Record<string, string>,
    );

    selectFileName.value = scripts[0].name;
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .mongodb-exec-script-apply-content-dialog {
    .editor-layout {
      display: flex;
      width: 100%;
      height: 100%;
      background: #2e2e2e;

      .editor-layout-left {
        width: 238px;
      }

      .editor-layout-right {
        position: relative;
        height: 100%;
        flex: 1;
      }
    }
  }
</style>
