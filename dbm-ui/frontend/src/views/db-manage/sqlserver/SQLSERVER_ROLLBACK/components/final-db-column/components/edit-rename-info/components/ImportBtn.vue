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

  import type { IValue } from '../Index.vue';

  interface Props {
    data: {
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    dbIgnoreName: string[];
    dbName: string[];
    renameInfoList: IValue[];
  }>({
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
    params.append('db_list', modelValue.value.dbName.join(','));
    params.append('ignore_db_list', modelValue.value.dbIgnoreName.join(','));
    params.append('db_excel', files[0]);
    isImportLoading.value = true;
    importDbStruct(params)
      .then((data) => {
        messageSuccess(t('导入成功'));
        modelValue.value.renameInfoList = data;
      })
      .finally(() => {
        isImportLoading.value = false;
      });
  };
</script>
