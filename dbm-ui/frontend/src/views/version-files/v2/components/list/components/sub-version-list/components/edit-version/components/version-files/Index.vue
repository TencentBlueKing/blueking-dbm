<template>
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
        ref="versionRowRefs"
        :able-to-delete="tableData.length > 1"
        :data="item"
        :is-applied="isApplied"
        :is-only-one-file="isOnlyOneFile"
        :selected-systems="selectedSystems"
        :selected-versions="selectedVersions"
        @delete="() => handleDeleteRow(index)"
        @system-os-type-change="handleOsTypeChange"
        @system-os-version-change="handleOsVersionChange">
      </VersionRow>
    </tbody>
  </table>
  <UploadFile
    :db-type="dbType"
    :pkg-type="pkgType"
    :uploaded-file-names="uploadedFileNames"
    :version="version"
    @success="handleAdd" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { random } from '@utils';

  import UploadFile from './components/UploadFile.vue';
  import VersionRow from './components/VersionRow.vue';

  interface Props {
    data?: Omit<(typeof tableData.value)[number], 'rowKey'>[];
    dbType: string;
    isApplied?: boolean;
    pkgType: string;
    version: string;
  }

  type Emits = (e: 'valueChange') => void;

  interface Exposes {
    getValue: () => ReturnType<InstanceType<typeof VersionRow>['getValue']>[] | null;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isApplied: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const versionRowRefs = ref<InstanceType<typeof VersionRow>[]>([]);
  const selectedSystems = ref<Set<string>>(new Set());
  const selectedVersions = ref<Record<string, Set<string>>>({});
  const tableData = ref<
    {
      id?: number;
      md5: string;
      name: string;
      path: string;
      rowKey: string;
      size: number;
      versions?: string[];
    }[]
  >([]);

  const uploadedFileNames = computed(() => tableData.value.map((item) => item.name));
  const isOnlyOneFile = computed(() => tableData.value.length === 1);

  watch(
    () => props.data,
    () => {
      tableData.value = props.data
        ? props.data.map((item) => ({
            ...item,
            rowKey: random(),
          }))
        : [];
    },
    { immediate: true },
  );

  const handleOsTypeChange = (isInit: boolean) => {
    if (!isInit) {
      emits('valueChange');
    }
    selectedSystems.value.clear();
    selectedVersions.value = {};
    versionRowRefs.value.forEach((item) => {
      const system = item.getSelectedSystem();
      if (!system) {
        return;
      }

      if (!selectedVersions.value[system]) {
        selectedVersions.value[system] = new Set();
      }
      selectedSystems.value.add(system);
      const versions = item.getSelectedVersions();
      versions.forEach((version) => {
        selectedVersions.value[system].add(version);
      });
    });
  };

  const handleOsVersionChange = () => {
    emits('valueChange');
  };

  const handleAdd = (fileInfo: { md5: string; name: string; path: string; size: number }) => {
    tableData.value.push({
      ...fileInfo,
      rowKey: random(),
    });
  };

  const handleDeleteRow = (index: number) => {
    tableData.value.splice(index, 1);
    emits('valueChange');
  };

  defineExpose<Exposes>({
    getValue() {
      if (tableData.value.length === 0) {
        return null;
      }

      const filesInfo = versionRowRefs.value.map((item) => item.getValue());
      if (filesInfo.some((item) => !item.permit_os.length || !item.permit_os_type)) {
        return null;
      }

      return filesInfo;
    },
  });
</script>
<style lang="less">
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
</style>
