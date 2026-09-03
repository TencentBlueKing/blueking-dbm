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
  <div
    class="version-files-table-container"
    :class="{ 'is-valid-error': isValidError }">
    <table class="version-files-table">
      <thead>
        <tr>
          <th style="width: 340px">{{ t('文件') }}</th>
          <th style="width: 152px">OS</th>
          <th style="width: 356px">{{ t('OS版本') }}</th>
          <th style="width: 64px"></th>
        </tr>
      </thead>
      <tbody>
        <VersionRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          v-model:permit-os="item.permit_os"
          v-model:permit-os-type="item.permit_os_type"
          :data="item"
          :is-applied="isApplied"
          :occupied-os-versions="occupiedOsVersionList[index]"
          :os-type-list="osTypeList"
          :os-version-list="osVersionList[index]"
          @delete="() => handleDeleteRow(index)"
          @os-type-change="() => handleOsTypeChange(index)"
          @os-version-change="() => handleOsVersionChange(index)" />
      </tbody>
    </table>
    <UploadFile
      ref="uploadFileRef"
      :db-type="dbType"
      :pkg-type="pkgType"
      :uploaded-file-names="uploadedFileNames"
      :version="version"
      @success="handleAdd" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listSupportSystems } from '@services/source/package';

  import { random } from '@utils';

  import UploadFile from './components/UploadFile.vue';
  import VersionRow from './components/VersionRow.vue';

  interface Props {
    data?: {
      id?: number;
      md5: string;
      name: string;
      path: string;
      permit_os?: string[];
      permit_os_type?: string;
      size: number;
    }[];
    dbType: string;
    isApplied?: boolean;
    pkgType: string;
    version: string;
  }

  type Emits = (e: 'valueChange') => void;

  /** 提交给接口的版本文件信息 */
  interface VersionFileInfo {
    id?: number;
    md5: string;
    name: string;
    path: string;
    permit_os: string[];
    permit_os_type: string;
    size: number;
  }

  interface FileRow extends VersionFileInfo {
    /** 已被应用、不可再移除的 OS 版本，只在编辑已应用版本时有值 */
    lockedOsList: string[];
    rowKey: string;
  }

  interface Exposes {
    getValue: () => VersionFileInfo[] | string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isApplied: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const uploadFileRef = ref<InstanceType<typeof UploadFile>>();
  const isValidError = ref(false);
  const tableData = ref<FileRow[]>([]);
  /** OS 类型 -> 该类型支持的 OS 版本 */
  const supportSystems = ref<Record<string, string[]>>({});

  const uploadedFileNames = computed(() => tableData.value.map((item) => item.name));
  const osTypeList = computed(() =>
    Object.keys(supportSystems.value).map((item) => ({
      label: item,
      value: item,
    })),
  );

  /** 每一行可选的 OS 版本，锁定项已经单独展示，不再进候选 */
  const osVersionList = computed(() =>
    tableData.value.map((row) => {
      const lockedSet = new Set(row.lockedOsList);
      return (supportSystems.value[row.permit_os_type] || [])
        .filter((item) => !lockedSet.has(item))
        .map((item) => ({
          label: item,
          value: item,
        }));
    }),
  );

  /** 每一行被其它文件占用的 OS 版本，key 为 OS 类型。任意两个文件不能覆盖同一个 OS 版本 */
  const occupiedOsVersionList = computed(() =>
    tableData.value.map((currentRow) => {
      const occupied: Record<string, Set<string>> = {};
      tableData.value.forEach((row) => {
        if (row === currentRow || !row.permit_os_type) {
          return;
        }
        if (!occupied[row.permit_os_type]) {
          occupied[row.permit_os_type] = new Set();
        }
        [...row.permit_os, ...row.lockedOsList].forEach((version) => {
          occupied[row.permit_os_type].add(version);
        });
      });
      return occupied;
    }),
  );

  useRequest(listSupportSystems, {
    onSuccess(data) {
      supportSystems.value = data;
    },
  });

  watch(
    [() => props.data, () => props.isApplied],
    () => {
      tableData.value = (props.data || []).map((item) => {
        // 接口用空数组表示覆盖该 OS 类型的全部版本，界面上用 all 这一项表达
        const permitOs = item.permit_os?.length ? item.permit_os.slice() : ['all'];
        // 已应用的版本文件，原有的 OS 版本锁定不可移除，只允许在此之外追加；
        // 覆盖全部版本时没有具体版本可锁，维持可编辑
        const isLocked = props.isApplied && permitOs[0] !== 'all';
        return {
          id: item.id,
          lockedOsList: isLocked ? permitOs : [],
          md5: item.md5,
          name: item.name,
          path: item.path,
          permit_os: isLocked ? [] : permitOs,
          permit_os_type: item.permit_os_type || '',
          rowKey: random(),
          size: item.size,
        };
      });
    },
    { immediate: true },
  );

  /** 某个文件占据了一个 OS 类型的全部版本后，同类型的其它文件要让位 */
  const releaseConflictRows = (index: number) => {
    const changedRow = tableData.value[index];
    if (!changedRow.permit_os.includes('all')) {
      return;
    }
    tableData.value.forEach((row, rowIndex) => {
      if (rowIndex === index || row.permit_os_type !== changedRow.permit_os_type) {
        return;
      }
      tableData.value[rowIndex].permit_os_type = '';
      tableData.value[rowIndex].permit_os = [];
    });
  };

  const handleOsTypeChange = (index: number) => {
    // 换 OS 类型后原有的版本选择作废，只有一个文件时默认覆盖全部版本
    tableData.value[index].permit_os = tableData.value.length === 1 ? ['all'] : [];
    emits('valueChange');
  };

  const handleOsVersionChange = (index: number) => {
    releaseConflictRows(index);
    emits('valueChange');
  };

  const handleAdd = (fileInfo: { md5: string; name: string; path: string; size: number }) => {
    tableData.value.push({
      ...fileInfo,
      lockedOsList: [],
      permit_os: [],
      permit_os_type: '',
      rowKey: random(),
    });
    emits('valueChange');
  };

  const handleDeleteRow = (index: number) => {
    uploadFileRef.value!.clearDuplicateTip();
    tableData.value.splice(index, 1);
    emits('valueChange');
  };

  defineExpose<Exposes>({
    getValue() {
      isValidError.value = false;
      if (tableData.value.length === 0) {
        isValidError.value = true;
        return t('请至少添加 1 个版本文件');
      }

      const filesInfo = tableData.value.map((row) => ({
        id: row.id,
        md5: row.md5,
        name: row.name,
        path: row.path,
        permit_os: [...row.permit_os, ...row.lockedOsList],
        permit_os_type: row.permit_os_type,
        size: row.size,
      }));
      if (filesInfo.some((item) => !item.permit_os.length || !item.permit_os_type)) {
        isValidError.value = true;
        return t('请补全版本文件信息');
      }

      return filesInfo;
    },
  });
</script>
<style lang="less">
  .version-files-table-container {
    width: 100%;
    border: 1px solid transparent;
    box-sizing: content-box;

    &.is-valid-error {
      border-color: #ed3f14;
    }

    .version-files-table {
      width: 100%;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 12px;
      table-layout: fixed;

      thead {
        border-bottom: 4px solid #fff;
      }

      th {
        padding-left: 16px;
        margin-bottom: 4px;
        font-weight: normal;
        color: #313238;
        background: #f0f1f5;
      }

      tbody {
        tr {
          border-bottom: 10px solid #fff;
        }
      }

      td {
        padding: 5px 16px;
        background: #f5f7fa;
      }
    }
  }
</style>
