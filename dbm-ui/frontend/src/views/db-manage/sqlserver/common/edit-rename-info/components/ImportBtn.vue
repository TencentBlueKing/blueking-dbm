<template>
  <span>
    <BkButton
      :disabled="isImportLoading"
      text
      theme="primary"
      @click="handleImport">
      <DbIcon
        class="mr-4"
        type="daoru" />
      {{ t('导入') }}
    </BkButton>
    <input
      ref="uploadRef"
      accept=".xlsx,.xls"
      style="position: absolute; width: 0; height: 0"
      type="file"
      @change="handleStartUpload" />
  </span>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { importDbStruct } from '@services/source/sqlserver';

  import { messageSuccess } from '@utils';

  interface Props {
    clusterId: number;
    dbName: string[];
    dbIgnoreName: string[];
  }

  interface Emits {
    (e: 'change', value: { db_name: string; target_db_name: string; rename_db_name: string }[]): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const uploadRef = ref<HTMLInputElement>();
  const isImportLoading = ref(false);

  const handleImport = () => {
    uploadRef.value!.click();
  };

  // 开始上传文件
  const handleStartUpload = (event: Event) => {
    const { files = [] } = event.target as HTMLInputElement;

    if (!files) {
      return;
    }
    const params = new FormData();
    params.append('cluster_id', `${props.clusterId}`);
    params.append('db_list', props.dbName.join(','));
    params.append('ignore_db_list', props.dbIgnoreName.join(','));
    params.append('db_excel', files[0]);
    isImportLoading.value = true;
    importDbStruct(params)
      .then((data) => {
        messageSuccess(t('导入成功'));
        emits('change', data);
      })
      .finally(() => {
        isImportLoading.value = false;
      });
  };
</script>
