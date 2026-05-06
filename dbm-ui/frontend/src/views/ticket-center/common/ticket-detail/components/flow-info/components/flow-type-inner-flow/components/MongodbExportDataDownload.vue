<template>
  <BkButton
    class="download-button"
    text
    theme="primary"
    @click="handleDownloadShow">
    <DbIcon
      class="download-line-button"
      type="download-line" />
    <span class="ml-2">{{ t('下载结果文件') }}</span>
  </BkButton>
  <BkDialog
    v-model:is-show="isShow"
    :title="t('下载结果文件')"
    :width="1140">
    <BkButton
      class="mb-8"
      :disabled="selected.length === 0"
      :loading="isBatchDownloading"
      @click="() => handleBatchDownload()">
      {{ t('批量下载') }}
    </BkButton>
    <PrimaryTable
      :data="dataList"
      row-key="cluster_id"
      :selected-row-keys="selectedRowKeys"
      @select-change="handleSelectChange">
      <TableColumn
        col-key="row-select"
        type="multiple"
        :width="40" />
      <TableColumn
        col-key="file_name"
        :title="t('文件名')" />
      <TableColumn
        col-key="size"
        :title="t('大小')"
        :width="160">
        <template #default="{ row }: { row: IDataRow }">
          {{ bytePretty(row.size) }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="cluster_id"
        :title="t('集群')">
        <template #default="{ row }: { row: IDataRow }">
          {{ clusters[row.cluster_id].immute_domain }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        :title="t('操作')"
        :width="120">
        <template #default="{ row, rowIndex }: { row: IDataRow; rowIndex: number }">
          <BkButton
            :loading="downloadLoadings[rowIndex]"
            text
            theme="primary"
            @click="handleDownload(row.file_path, rowIndex)">
            {{ t('下载') }}
          </BkButton>
          <BkButton
            class="ml-8"
            :loading="fileLoadings[rowIndex]"
            text
            theme="primary"
            @click="handleCopyUrl(row.file_path, rowIndex)">
            {{ t('复制链接') }}
          </BkButton>
        </template>
      </TableColumn>
    </PrimaryTable>
    <template #footer>
      <BkButton @click="handleClose">{{ t('关闭') }}</BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';
  import { batchCreateBkrepoAccessToken, createBkrepoAccessToken } from '@services/source/storage';

  import { bytePretty, downloadUrl, execCopy, generateBkRepoDownloadUrl } from '@utils';

  type IDataRow = (typeof dataList)[number];

  interface Props {
    ticketDetail: TicketModel<Mongodb.DataExport>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShow = ref(false);
  const isBatchDownloading = ref(false);
  const downloadLoadings = ref<boolean[]>([]);
  const fileLoadings = ref<boolean[]>([]);
  const selectedRowKeys = ref<number[]>([]);
  const selected = shallowRef<IDataRow[]>([]);

  const { clusters, exported_files: exportFiles } = props.ticketDetail.details;
  const dataList = Object.entries(exportFiles).map(([clusterId, fileItem]) => {
    return Object.assign({}, fileItem, { cluster_id: Number(clusterId) });
  });

  const handleDownloadShow = () => {
    isShow.value = true;
  };

  const handleClose = () => {
    isShow.value = false;
    selectedRowKeys.value = [];
    selected.value = [];
  };

  const handleSelectChange = (value: (string | number)[], { selectedRowData }: { selectedRowData: unknown[] }) => {
    selectedRowKeys.value = value as number[];
    selected.value = selectedRowData as IDataRow[];
  };

  const handleDownload = async (filePath: string, index: number) => {
    downloadLoadings.value[index] = true;
    try {
      const tokenResult = await createBkrepoAccessToken({ file_path: filePath });
      const url = generateBkRepoDownloadUrl(tokenResult);
      downloadUrl(url);
    } finally {
      downloadLoadings.value[index] = false;
    }
  };

  const handleBatchDownload = () => {
    if (selected.value.length === 0) {
      return;
    }
    isBatchDownloading.value = true;
    const paths = selected.value.map((item) => item.file_path);
    batchCreateBkrepoAccessToken({ file_path_list: paths })
      .then((tokenResultList) => {
        selectedRowKeys.value = [];
        selected.value = [];

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
        isBatchDownloading.value = false;
      });
  };

  const handleCopyUrl = (filePath: string, index: number) => {
    fileLoadings.value[index] = true;
    createBkrepoAccessToken({ file_path: filePath })
      .then((tokenResult) => {
        const url = generateBkRepoDownloadUrl(tokenResult);
        execCopy(url, t('复制成功，共n条', { n: 1 }));
      })
      .finally(() => {
        fileLoadings.value[index] = false;
      });
  };
</script>
