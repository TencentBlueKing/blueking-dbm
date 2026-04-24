<template>
  <BkPopConfirm
    :confirm-config="{
      loading: downloadPackagesLoading,
      disabled: !checkedPackages.length,
    }"
    placement="bottom"
    :popover-options="{
      disabled: data?.packages.length === 1,
      extCls: 'download-package-confirm',
    }"
    :title="t('请勾选需要下载的文件')"
    trigger="click"
    :width="380"
    @after-hidden="handleAfterHidden"
    @confirm="handleDownloadPackages">
    <template #content>
      <div class="package-list">
        <BkCheckboxGroup v-model="checkedPackages">
          <BkCheckbox
            v-for="item in props.data?.packages"
            :key="item.id"
            :label="item.path">
            {{ item.name }}
          </BkCheckbox>
        </BkCheckboxGroup>
        <div class="select-all-main">
          <BkCheckbox
            v-model="isSelectAll"
            @change="handleSelectAllChange">
            {{ t('全选') }}
          </BkCheckbox>
        </div>
      </div>
    </template>
    <BkButton
      class="ml-12"
      :loading="downloadSinglePackageLoading"
      size="small"
      text
      theme="primary"
      @click="handleDownloadSinglePackage">
      {{ t('下载文件') }}
    </BkButton>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { batchCreateBkrepoAccessToken, createBkrepoAccessToken } from '@services/source/storage';

  import { downloadUrl, generateBkRepoDownloadUrl, messageSuccess } from '@utils';

  interface Props {
    data?: DbVersionModel;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });

  const { t } = useI18n();

  const downloadPackagesLoading = ref(false);
  const downloadSinglePackageLoading = ref(false);
  const checkedPackages = ref<string[]>([]);
  const isSelectAll = ref(false);

  watch(
    checkedPackages,
    () => {
      isSelectAll.value = checkedPackages.value.length === props.data?.packages.length;
    },
    {
      immediate: true,
    },
  );

  const handleSelectAllChange = (isSelectAll: boolean) => {
    if (isSelectAll) {
      checkedPackages.value = props.data?.packages.map((item) => item.path) || [];
    } else {
      checkedPackages.value = [];
    }
  };

  const handleDownloadPackages = async () => {
    try {
      downloadPackagesLoading.value = true;
      const tokenResult = await batchCreateBkrepoAccessToken({ file_path_list: checkedPackages.value });
      const urls = tokenResult.map((item) => generateBkRepoDownloadUrl(item));
      urls.forEach((url) => downloadUrl(url));
      messageSuccess(t('下载成功'));
    } finally {
      downloadPackagesLoading.value = false;
    }
  };

  const handleDownloadSinglePackage = async () => {
    if (props.data?.packages?.length && props.data.packages.length > 1) {
      return;
    }

    try {
      downloadSinglePackageLoading.value = true;
      const tokenResult = await createBkrepoAccessToken({ file_path: props.data!.packages[0].path });
      const url = generateBkRepoDownloadUrl(tokenResult);
      downloadUrl(url);
      messageSuccess(t('下载成功'));
    } finally {
      downloadSinglePackageLoading.value = false;
    }
  };

  const handleAfterHidden = () => {
    checkedPackages.value = [];
    isSelectAll.value = false;
  };
</script>

<style lang="less">
  .download-package-confirm {
    .bk-pop-confirm {
      position: relative;

      .select-all-main {
        position: absolute;
        bottom: 3px;
        left: 0;
      }
    }
    .package-list {
      max-height: 200px;
      overflow-y: auto;
      margin-bottom: 20px;

      .bk-checkbox-group {
        display: flex;
        flex-direction: column;
        gap: 12px;

        .bk-checkbox {
          margin-left: 0 !important;
        }
      }
    }
  }
</style>
