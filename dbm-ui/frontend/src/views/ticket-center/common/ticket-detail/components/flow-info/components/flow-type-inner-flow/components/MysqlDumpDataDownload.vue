<template>
  <BkButton
    class="download-button"
    text
    theme="primary"
    @click="handleDownload(`${details.ticket_data.dump_file_path}/`)">
    <DbIcon
      class="download-line-button"
      type="download-line" />
    <span class="ml-2">{{ t('下载结果文件') }}</span>
  </BkButton>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { createBkrepoAccessToken } from '@services/source/storage';

  import { downloadUrl } from '@utils';

  interface Props {
    details: {
      ticket_data: {
        dump_file_path: string;
      };
    };
  }

  defineProps<Props>();

  const { t } = useI18n();

  const handleDownload = async (filePath: string) => {
    const tokenResult = await createBkrepoAccessToken({ file_path: filePath });
    const url = `${tokenResult.url}/generic/temporary/download/${tokenResult.project}/${tokenResult.repo}/${tokenResult.path}?token=${tokenResult.token}&download=true`;
    downloadUrl(url);
  };
</script>
