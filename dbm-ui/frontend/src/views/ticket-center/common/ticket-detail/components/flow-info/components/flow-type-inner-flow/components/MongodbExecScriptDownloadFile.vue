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
    <BkTable
      :data="details.ticket_data.rules"
      :height="460">
      <BkTableColumn
        field="path"
        :label="t('路径')" />
      <BkTableColumn
        :label="t('操作')"
        :width="100">
        <template #default="{ data: rowData }: { data: Props['details']['ticket_data']['rules'][number] }">
          <BkButton
            text
            theme="primary"
            @click="handleDownloadFile(rowData.path)">
            {{ t('下载') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </BkTable>
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
