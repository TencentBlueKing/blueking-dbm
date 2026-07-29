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
    class="ml-12"
    text
    theme="primary"
    @click="handleExport">
    <DbIcon
      class="mr-4"
      type="daochu-2" />
    {{ t('导出') }}
  </BkButton>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { exportExcelFile } from '@utils';

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
    renameInfoList: IValue[];
  }>({
    required: true,
  });

  const { t } = useI18n();
  // 导出文件
  const handleExport = () => {
    const formatData = modelValue.value.renameInfoList.map((item) => ({
      [t('已有库新名')]: item.rename_db_name,
      [t('恢复后库名')]: item.target_db_name,
      [t('源库名')]: item.db_name,
    }));
    const colsWidths = [{ width: 40 }, { width: 40 }, { width: 40 }];

    exportExcelFile(
      formatData,
      colsWidths,
      `集群（${props.data.srcCluster.master_domain}）`,
      `${t('SQLServer定点回档手动修改回档DB名')}_${props.data.srcCluster.master_domain}.xlsx`,
    );
  };
</script>
