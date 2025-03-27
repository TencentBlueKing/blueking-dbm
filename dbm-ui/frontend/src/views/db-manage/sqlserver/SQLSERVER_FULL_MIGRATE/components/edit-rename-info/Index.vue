<template>
  <div>
    <div class="edit-name-box">
      <ClusterDb v-model="modelValue" />
      <div style="margin-top: 24px; margin-bottom: 16px; font-size: 12px">
        <span style="font-weight: bold; color: #313238">{{ t('DB 列表') }}</span>
        <I18nT
          keypath="（共 n 个）"
          style="color: #63656e">
          {{ modelValue.renameInfoList.length }}
        </I18nT>
        <ImportBtn
          v-model="modelValue.renameInfoList"
          class="ml-12"
          :data="modelValue" />
        <ExportBtn
          class="ml-12"
          :data="modelValue" />
      </div>
      <RenameList
        v-model="modelValue.renameInfoList"
        :cluster-data="modelValue" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import ClusterDb from './components/ClusterDb.vue';
  import ExportBtn from './components/ExportBtn.vue';
  import ImportBtn from './components/ImportBtn.vue';
  import RenameList from './components/rename-list/Index.vue';

  export type IValue = {
    db_name: string;
    rename_cluster_list: number[];
    rename_db_name: string;
    target_db_name: string;
  };

  const modelValue = defineModel<{
    dbIgnoreName: string[];
    dbName: string[];
    dstCluster: {
      id: number;
      master_domain: string;
    }[];
    renameInfoList: IValue[];
    srcCluster: {
      id: number;
      master_domain: string;
    };
  }>({
    required: true,
  });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .edit-name-box {
    padding: 20px 24px;
  }
</style>
