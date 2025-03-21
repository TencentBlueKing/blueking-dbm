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

  export type IValue = ServiceReturnType<typeof importDbStruct>[number];

  interface Props {
    data: {
      dbIgnoreName: string[];
      dbName: string[];
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<IValue[]>({
    required: true,
  });

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
    params.append('cluster_id', `${props.data.srcCluster.id}`);
    params.append('db_list', props.data.dbName.join(','));
    params.append('ignore_db_list', props.data.dbIgnoreName.join(','));
    params.append('db_excel', files[0]);
    isImportLoading.value = true;
    importDbStruct(params)
      .then((data) => {
        messageSuccess(t('导入成功'));
        modelValue.value = data;
      })
      .finally(() => {
        isImportLoading.value = false;
      });
  };
</script>
