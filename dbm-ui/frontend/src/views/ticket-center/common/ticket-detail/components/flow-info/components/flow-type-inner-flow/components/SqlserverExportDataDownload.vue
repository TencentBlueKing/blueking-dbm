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
    class="download-button"
    text
    theme="primary"
    @click="handleShow">
    <DbIcon
      class="download-line-button"
      type="download-line" />
    <span class="ml-2">{{ t('下载结果文件') }}</span>
  </BkButton>
  <BkDialog
    dialog-type="show"
    :is-show="isShow"
    :title="t('下载结果文件')"
    :width="1080"
    @closed="handleClose">
    <BkButton
      class="mb-16"
      :disabled="disabled"
      :loading="state.isBatchDownloading"
      @click="handleBatchDownload">
      {{ t('批量下载') }}
    </BkButton>
    <BkTable
      :data="state.data"
      :height="460"
      @checkbox-all="handleTableAllSelected"
      @checkbox-change="handleTableSelected">
      <BkTableColumn
        fixed="left"
        type="checkbox"
        :width="60" />
      <BkTableColumn
        field="name"
        fixed="left"
        :label="t('文件名')"
        :min-width="300" />
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
        :width="260">
        <template #default="{data}: {data: RowData}">
          {{ details.ticket_data.clusters[data.cluster_id].immute_domain }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        fixed="right"
        :label="t('操作')"
        :width="150">
        <template #default="{data, rowIndex}: {data: RowData, rowIndex: number}">
          <BkButton
            class="mr-8"
            :loading="state.downloadLoadings[rowIndex]"
            text
            theme="primary"
            @click="handleDownloadFile(data, rowIndex)">
            {{ t('下载') }}
          </BkButton>
          <BkButton
            :loading="state.fileLoadings[rowIndex]"
            text
            theme="primary"
            @click="handleCopy(data, rowIndex)">
            {{ t('复制链接') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </BkTable>
  </BkDialog>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { DetailClusters } from '@services/model/ticket/details/common';
  import { batchCreateBkrepoAccessToken, createBkrepoAccessToken } from '@services/source/storage';

  import { bytePretty, downloadUrl, execCopy, generateBkRepoDownloadUrl } from '@utils';

  interface Props {
    details: {
      ticket_data: {
        bk_biz_id: number;
        cluster_ids: number[];
        clusters: DetailClusters;
        created_by: string;
        dump_file_list: {
          cluster_id: number;
          name: string;
          path: string;
          size: number;
        }[];
        dump_file_names: string[];
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
    data: [] as RowData[],
    downloadLoadings: [] as boolean[],
    fileLoadings: [] as boolean[],
    isBatchDownloading: false,
    selected: [] as RowData[],
  });

  const disabled = computed(() => {
    return state.selected.length === 0;
  });

  watch(isShow, (isShow) => {
    if (isShow) {
      state.data = _.cloneDeep(props.details.ticket_data.dump_file_list);
    }
  });

  const handleShow = () => {
    isShow.value = true;
  };

  /**
   * 表格选中
   */
  function handleTableSelected({ checked, row }: { checked: boolean; data: RowData[]; row: RowData }) {
    // 单选 checkbox 选中
    if (checked) {
      const toggleIndex = state.selected.findIndex((item) => item.cluster_id === row.cluster_id);
      if (toggleIndex === -1) {
        state.selected.push(row);
      }
      return;
    }

    // 单选 checkbox 取消选中
    const toggleIndex = state.selected.findIndex((item) => item.cluster_id === row.cluster_id);
    if (toggleIndex > -1) {
      state.selected.splice(toggleIndex, 1);
    }
  }

  /**
   * 全选
   */
  function handleTableAllSelected({ checked }: { checked: boolean }) {
    state.selected = checked ? [...state.data] : [];
  }

  /**
   * 批量下载文件
   */
  function handleBatchDownload() {
    if (state.selected.length === 0) {
      return;
    }
    state.isBatchDownloading = true;
    const paths = state.selected.map((item) => item.path);
    batchCreateBkrepoAccessToken({ file_path_list: paths })
      .then((tokenResultList) => {
        const urls = tokenResultList.map((item) => generateBkRepoDownloadUrl(item));
        let index = 0;
        const downloadNext = () => {
          if (index < urls.length) {
            downloadUrl(urls[index]);
            index++;
            setTimeout(downloadNext, 600);
          }
        };
        downloadNext();
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
    Object.assign(state, {
      data: [],
      downloadLoadings: [],
      fileLoadings: [],
      isBatchDownloading: false,
      selected: [],
    });
  }
</script>
