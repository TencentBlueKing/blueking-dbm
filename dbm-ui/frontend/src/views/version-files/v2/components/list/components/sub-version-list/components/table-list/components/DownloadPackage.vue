<template>
  <BkButton
    class="ml-12"
    :loading="downloadSinglePackageLoading"
    size="small"
    text
    theme="primary"
    @click="handleDownloadClick">
    {{ t('下载') }}
  </BkButton>
  <DbDialog
    v-model:is-show="isShow"
    class="download-package-dialog"
    :confirm-button-disable-info="{ disabled: !checkedPackages.length, tooltips: { content: '', disabled: true } }"
    :confirm-handler="handleDownloadPackages"
    :confirm-text="t('下载')"
    quick-close
    render-directive="if"
    :title="t('下载版本文件')"
    :width="480"
    @closed="handleDialogClosed">
    <div class="package-list">
      <BkCheckbox
        v-model="isSelectAll"
        @change="handleSelectAllChange">
        {{ t('全选') }}
      </BkCheckbox>
      <BkCheckboxGroup v-model="checkedPackages">
        <BkCheckbox
          v-for="item in data.packages"
          :key="item.id"
          :label="item.path">
          {{ item.name }}
        </BkCheckbox>
      </BkCheckboxGroup>
    </div>
  </DbDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { batchCreateBkrepoAccessToken, createBkrepoAccessToken } from '@services/source/storage';

  import { downloadUrl, generateBkRepoDownloadUrl, messageSuccess } from '@utils';

  interface Props {
    data: DbVersionModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShow = ref(false);
  const downloadSinglePackageLoading = ref(false);
  const checkedPackages = ref<string[]>([]);
  const isSelectAll = ref(false);

  watch(
    checkedPackages,
    () => {
      isSelectAll.value = checkedPackages.value.length === props.data.packages.length;
    },
    {
      immediate: true,
    },
  );

  const handleSelectAllChange = (isSelectAll: boolean) => {
    if (isSelectAll) {
      checkedPackages.value = props.data.packages.map((item) => item.path) || [];
    } else {
      checkedPackages.value = [];
    }
  };

  const handleDownloadClick = async () => {
    if (props.data.packages?.length > 1) {
      checkedPackages.value = props.data.packages.map((item) => item.path);
      isSelectAll.value = true;
      isShow.value = true;
      return;
    }

    try {
      downloadSinglePackageLoading.value = true;
      const tokenResult = await createBkrepoAccessToken({ file_path: props.data.packages[0].path });
      const url = generateBkRepoDownloadUrl(tokenResult);
      downloadUrl(url);
      messageSuccess(t('下载成功'));
    } finally {
      downloadSinglePackageLoading.value = false;
    }
  };

  const handleDownloadPackages = async () => {
    const tokenResult = await batchCreateBkrepoAccessToken({ file_path_list: checkedPackages.value });
    const urls = tokenResult.map((item) => generateBkRepoDownloadUrl(item));
    urls.forEach((url) => downloadUrl(url));
    messageSuccess(t('下载成功'));
  };

  const handleDialogClosed = () => {
    checkedPackages.value = [];
    isSelectAll.value = false;
  };
</script>

<style lang="less">
  .download-package-dialog {
    .package-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 320px;
      overflow-y: auto;

      .bk-checkbox {
        margin-left: 0 !important;
      }

      .bk-checkbox-group {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
    }
  }
</style>
