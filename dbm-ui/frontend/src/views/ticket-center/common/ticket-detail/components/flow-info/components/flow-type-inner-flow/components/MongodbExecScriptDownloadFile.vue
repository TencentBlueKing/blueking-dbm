<template>
  <BkButton
    text
    theme="primary"
    @click="handleShowFile">
    {{ t('查看结果文件') }}
  </BkButton>
  <BkDialog
    v-model:is-show="isShow"
    :title="t('查看结果文件')"
    :width="1140">
    <PrimaryTable
      :data="details.ticket_data.rules"
      :height="460"
      row-key="path">
      <TableColumn
        col-key="path"
        :title="t('路径')" />
      <TableColumn
        col-key="operation"
        :title="t('操作')"
        :width="100">
        <template #default="{ row }: { row: Props['details']['ticket_data']['rules'][number] }">
          <BkButton
            text
            theme="primary"
            @click="handleDownloadFile(row.path)">
            {{ t('下载') }}
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

  import { createBkrepoAccessToken } from '@services/source/storage';

  import { downloadUrl, generateBkRepoDownloadUrl } from '@utils';

  interface Props {
    details: {
      ticket_data: {
        rules: {
          cluster_id: number;
          path: string;
        }[];
      };
    };
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isShow = ref(false);

  const handleShowFile = () => {
    isShow.value = true;
  };

  const handleDownloadFile = (path: string) => {
    createBkrepoAccessToken({ file_path: path }).then((tokenResult) => {
      const url = generateBkRepoDownloadUrl(tokenResult);
      downloadUrl(url);
    });
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>
