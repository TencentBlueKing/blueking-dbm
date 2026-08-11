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
    class="result-files"
    dialog-type="show"
    :is-show="isShow"
    :title="t('查看结果文件')"
    :width="1140"
    @closed="handleClose">
    <BkLoading :loading="state.isLoading">
      <PrimaryTable
        class="result-files-table"
        :data="state.data"
        :height="460">
        <TableColumn
          col-key="name"
          ellipsis
          fixed="left"
          :min-width="240"
          :title="t('目录')" />
        <TableColumn
          col-key="size_display"
          ellipsis
          :title="t('大小')"
          :width="100" />
        <TableColumn
          col-key="domain"
          ellipsis
          :title="t('集群')"
          :width="240" />
        <TableColumn
          col-key="created_time"
          ellipsis
          :title="t('提取时间')"
          :width="250" />
        <TableColumn
          col-key="operation"
          fixed="right"
          :title="t('操作')"
          :width="150">
          <template #default="{ row: data, rowIndex: index }: { row: KeyFileItem; rowIndex: number }">
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
              @click="getDownloadUrl(data, index)">
              {{ t('复制文件地址') }}
            </BkButton>
          </template>
        </TableColumn>
        <template #empty>
          <EmptyStatus
            :is-anomalies="isAnomalies"
            :is-searching="false"
            @refresh="fetchKeyFiles" />
        </template>
      </PrimaryTable>
    </BkLoading>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { createBkrepoAccessToken } from '@services/source/storage';
  import { getKeyFiles } from '@services/source/taskflow';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { downloadUrl, execCopy, generateBkRepoDownloadUrl } from '@utils';

  type KeyFileItem = ServiceReturnType<typeof getKeyFiles>[number];

  interface Props {
    id: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isAnomalies = ref(false);
  const isShow = ref(false);

  const state = reactive({
    data: [] as KeyFileItem[],
    downloadLoadings: [] as boolean[],
    fileLoadings: [] as boolean[],
    isLoading: false,
  });

  watch(isShow, () => {
    if (isShow.value) {
      fetchKeyFiles();
    }
  });

  const handleShow = () => {
    isShow.value = true;
  };

  /**
   * 获取结果文件列表
   */
  function fetchKeyFiles() {
    state.isLoading = true;
    getKeyFiles({ rootId: props.id })
      .then((res) => {
        state.data = res;
        state.downloadLoadings = res.map(() => false);
        state.fileLoadings = res.map(() => false);
        isAnomalies.value = false;
      })
      .catch(() => {
        state.data = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  /**
   * 获取结果文件地址
   */
  function getDownloadUrl(data: KeyFileItem, index: number) {
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
  function handleDownloadFile(data: KeyFileItem, index: number) {
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
    state.data = [];
    state.downloadLoadings = [];
    state.fileLoadings = [];
  }
</script>

<style lang="less" scoped>
  .result-files {
    .result-files-table {
      :deep(.cluster-name) {
        line-height: 16px;

        .cluster-name-alias {
          color: @light-gray;
        }
      }
    }
  }
</style>
