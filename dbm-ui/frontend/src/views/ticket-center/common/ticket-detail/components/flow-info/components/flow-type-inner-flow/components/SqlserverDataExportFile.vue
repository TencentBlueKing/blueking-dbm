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
  <BkButton
    text
    theme="primary"
    @click="handleShow">
    {{ t('查看结果文件') }}
  </BkButton>
  <BkDialog
    dialog-type="show"
    :is-show="isShow"
    :title="t('查看结果文件')"
    :width="1080"
    @closed="handleClose">
    <BkButton
      class="mb-16"
      @click="handleCopyAll">
      {{ t('复制全部链接') }}
    </BkButton>
    <DbOriginalTable
      :data="details.ticket_data.dump_file_list"
      :height="460">
      <BkTableColumn
        field="name"
        fixed="left"
        :label="t('文件名')"
        :min-width="280" />
      <BkTableColumn
        field="size"
        :label="t('大小')"
        :width="120">
        <template #default="{data}: {data: RowData}">
          {{ data.size ? bytePretty(data.size) : '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="cluster_id"
        :label="t('集群')"
        :width="280">
        <template #default="{data}: {data: RowData}">
          {{ details.ticket_data.clusters[data.cluster_id].immute_domain }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        fixed="right"
        :label="t('操作')"
        :width="150">
        <template #default="{data, index}: {data: RowData, index: number}">
          <BkButton
            class="mr-8"
            :loading="state.downloadLoadings[index]"
            text
            theme="primary"
            @click="handleDownloadFile(data, index)">
            {{ t('下载') }}
          </BkButton>
          <BkButton
            :loading="state.fileLoadings[index]"
            text
            theme="primary"
            @click="handleCopy(data, index)">
            {{ t('复制链接') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </DbOriginalTable>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { DetailClusters } from '@services/model/ticket/details/common';
  import { createBkrepoAccessToken } from '@services/source/storage';

  import { bytePretty, downloadUrl, execCopy, generateBkRepoDownloadUrl } from '@utils';

  interface Props {
    details: {
      ticket_data: {
        bk_biz_id: number;
        cluster_ids: number[];
        clusters: DetailClusters;
        created_by: string;
        dump_file_names: string[];
        dump_file_list: {
          cluster_id: number;
          size: number;
          name: string;
          path: string;
        }[];
        execute_objects: {
          dbnames: string[];
          sql_files: string[];
        }[];
        path: string;
        select_role: string;
        ticket_type: string;
        uid: number;
      };
    };
  }

  type RowData = Props['details']['ticket_data']['dump_file_list'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShow = ref(false);

  const state = reactive({
    downloadLoadings: [] as boolean[],
    fileLoadings: [] as boolean[],
    isBatchDownloading: false,
  });

  const handleShow = () => {
    isShow.value = true;
  };

  /**
   * 复制全部文件链接
   */
  function handleCopyAll() {
    state.isBatchDownloading = true;
    const filePaths = props.details.ticket_data.dump_file_list.map((item) => item.path);
    Promise.all(filePaths.map((path) => createBkrepoAccessToken({ file_path: path })))
      .then((tokenResults) => {
        const urls = tokenResults.map((token) => generateBkRepoDownloadUrl(token));
        execCopy(urls.join('\n'), t('复制成功，共n条', { n: urls.length }));
      })
      .finally(() => {
        state.isBatchDownloading = false;
      });
  }

  /**
   * 复制单个文件链接
   */
  function handleCopy(data: RowData, index: number) {
    state.fileLoadings[index] = true;
    createBkrepoAccessToken({ file_path: data.path })
      .then((tokenResult) => {
        const url = generateBkRepoDownloadUrl(tokenResult);
        execCopy(url, t('复制成功，共n条', { n: 1 }));
      })
      .finally(() => {
        state.fileLoadings[index] = false;
      });
  }

  /**
   * 下载单个文件
   */
  function handleDownloadFile(data: RowData, index: number) {
    state.downloadLoadings[index] = true;
    createBkrepoAccessToken({ file_path: data.path })
      .then((tokenResult) => {
        const url = generateBkRepoDownloadUrl(tokenResult);
        downloadUrl(url);
      })
      .finally(() => {
        state.downloadLoadings[index] = false;
      });
  }

  function handleClose() {
    isShow.value = false;
    state.downloadLoadings = [];
    state.fileLoadings = [];
  }
</script>
