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
  <BkTable :data="ticketDetails.details.cluster_info">
    <BkTableColumn
      fixed="left"
      :label="t('集群')"
      :min-width="250">
      <template #default="{ data }: { data: IRowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('变更 DB')">
      <template #default="{ data }: { data: IRowData }">
        <TagBlock :data="data.execute_db" />
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('SQL 来源')">
      {{ ticketDetails.details.import_mode === 'manual' ? t('手动输入') : t('SQL文件') }}
    </InfoItem>
    <InfoItem :label="t('脚本执行内容')">
      <BkButton
        text
        theme="primary"
        @click="handleClickFile">
        {{ t('点击查看') }}
      </BkButton>
    </InfoItem>
  </InfoList>
  <BkSideslider
    class="oracle-exec-script-apply-content-dialog"
    :is-show="isShow"
    render-directive="if"
    :title="t('执行脚本变更_内容详情')"
    :width="960"
    :z-index="99999"
    @closed="handleClose">
    <BkLoading :loading="isContentLoading">
      <div class="editor-layout">
        <div class="editor-layout-left">
          <RenderFileList
            v-model="localSelectFileName"
            :data="ticketDetails.details.script_files" />
        </div>
        <div class="editor-layout-right">
          <RenderFileContent
            :db-types="DBTypes.ORACLE"
            :model-value="currentFileContent"
            readonly
            :title="localSelectFileName" />
        </div>
      </div>
    </BkLoading>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type Oracle } from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';

  import { DBTypes, TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import RenderFileContent from '@views/ticket-center/common/ticket-detail/components/common/SqlFileContent.vue';
  import RenderFileList from '@views/ticket-center/common/ticket-detail/components/common/SqlFileList.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type IRowData = Props['ticketDetails']['details']['cluster_info'][number];

  interface Props {
    ticketDetails: TicketModel<Oracle.ImportSqlFile>;
  }

  defineOptions({
    name: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const localSelectFileName = ref('');
  const fileContentMap = shallowRef<Record<string, string>>({});

  const currentFileContent = computed(() => fileContentMap.value[localSelectFileName.value] || '');

  const { loading: isContentLoading, run: runBatchFetchFile } = useRequest(
    () => {
      const filePathList = props.ticketDetails.details.script_files.map((item) =>
        [props.ticketDetails.details.path, item].join('/'),
      );

      return batchFetchFile({
        file_path_list: filePathList,
      });
    },
    {
      manual: true,
      onSuccess(result) {
        fileContentMap.value = result.reduce<Record<string, string>>((result, fileInfo) => {
          const fileName = fileInfo.path.split('/').pop() as string;
          return Object.assign(result, {
            [fileName]: fileInfo.content,
          });
        }, {});
      },
    },
  );

  watch(
    isShow,
    () => {
      if (isShow.value) {
        localSelectFileName.value = props.ticketDetails.details.script_files[0];
        runBatchFetchFile();
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickFile = () => {
    isShow.value = true;
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .oracle-exec-script-apply-content-dialog {
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
