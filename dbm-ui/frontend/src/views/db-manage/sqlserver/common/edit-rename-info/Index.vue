<template>
  <div>
    <div class="edit-name-box">
      <RenderClusterDb
        :cluster-id="clusterId"
        :db-ignore-name="localDbIgnoreName"
        :db-name="localDbName"
        @change="handleClusterDbChange" />
      <div style="margin-top: 24px; margin-bottom: 16px; font-size: 12px">
        <span style="font-weight: bold; color: #313238">{{ t('DB 列表') }}</span>
        <I18nT
          keypath="（共 n 个）"
          style="color: #63656e">
          {{ localRenameInfoList.length }}
        </I18nT>
        <ImportBtn
          class="ml-12"
          :cluster-id="clusterId"
          :db-ignore-name="localDbIgnoreName"
          :db-name="localDbName"
          @change="handleImportChange" />
        <ExportBtn
          class="ml-12"
          :cluster-id="clusterId"
          :data="localRenameInfoList" />
      </div>
      <RenderRenameList
        :key="updateRefreshKey"
        ref="dbListRef"
        v-model="localRenameInfoList"
        :db-ignore-name="localDbIgnoreName"
        :db-name="localDbName"
        :target-cluster-id="targetClusterId" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderClusterDb from './components/ClusterDb.vue';
  import ExportBtn from './components/ExportBtn.vue';
  import ImportBtn from './components/ImportBtn.vue';
  import RenderRenameList from './components/rename-list/Index.vue';

  export interface IValue {
    db_name: string;
    target_db_name: string;
    rename_db_name: string;
  }

  interface Props {
    clusterId: number;
    targetClusterId: number;
    dbName: string[];
    dbIgnoreName: string[];
    renameInfoList: IValue[];
  }

  interface Expose {
    submit: () => Promise<{
      dbName: Props['dbName'];
      dbIgnoreName: Props['dbIgnoreName'];
      renameInfoList: IValue[];
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dbListRef = ref<InstanceType<typeof RenderRenameList>>();

  const localDbName = ref(props.dbName);
  const localDbIgnoreName = ref(props.dbIgnoreName);
  const localRenameInfoList = ref<IValue[]>([]);
  const updateRefreshKey = ref(0);

  let isInnerChange = false;
  watch(
    () => [props.clusterId, props.dbName, props.dbIgnoreName, props.renameInfoList],
    () => {
      if (isInnerChange) {
        isInnerChange = false;
        return;
      }

      localDbName.value = props.dbName;
      localDbIgnoreName.value = props.dbIgnoreName;
      // 使用上一次编辑的值
      localRenameInfoList.value = [...props.renameInfoList];
      updateRefreshKey.value = Date.now();
    },
    {
      immediate: true,
    },
  );

  const handleClusterDbChange = (payload: { dbName: string[]; dbIgnoreName: string[]; renameInfoList: IValue[] }) => {
    localDbName.value = payload.dbName;
    localDbIgnoreName.value = payload.dbIgnoreName;
    localRenameInfoList.value = payload.renameInfoList;
    updateRefreshKey.value = Date.now();
  };

  const handleImportChange = (value: IValue[]) => {
    localRenameInfoList.value = value;
    updateRefreshKey.value = Date.now();
  };

  defineExpose<Expose>({
    submit() {
      isInnerChange = true;
      return dbListRef.value!.getValue().then(() => ({
        dbName: localDbName.value,
        dbIgnoreName: localDbIgnoreName.value,
        renameInfoList: localRenameInfoList.value,
      }));
    },
  });
</script>
<style lang="less" scoped>
  .edit-name-box {
    padding: 20px 24px;

    :deep(.bk-vxe-table) {
      .vxe-cell {
        padding: 0 !important;
      }

      .bk-form-content {
        margin-left: 0 !important;
      }
    }
  }
</style>
