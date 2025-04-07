<template>
  <BkSideslider
    v-model:is-show="isShow"
    :width="900">
    <template #header>
      <span>{{ t('手动修改迁移的 DB 名') }}</span>
      <BkTag class="ml-8">{{ data.srcCluster.master_domain }}</BkTag>
    </template>
    <div class="edit-name-box">
      <ClusterDb
        v-model="modelValue"
        :data="data"
        @change="updateTableKey" />
      <div style="margin-top: 24px; margin-bottom: 16px; font-size: 12px">
        <span style="font-weight: bold; color: #313238">{{ t('DB 列表') }}</span>
        <I18nT
          keypath="（共 n 个）"
          style="color: #63656e">
          {{ modelValue.renameInfoList.length }}
        </I18nT>
        <ImportBtn
          v-model="modelValue"
          class="ml-12"
          :data="data" />
        <ExportBtn
          v-model="modelValue"
          class="ml-12"
          :data="data" />
      </div>
      <RenameList
        :key="tableKey"
        v-model="modelValue"
        :data="data" />
    </div>
    <template #footer>
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import ClusterDb from './components/ClusterDb.vue';
  import ExportBtn from './components/ExportBtn.vue';
  import ImportBtn from './components/ImportBtn.vue';
  import RenameList from './components/RenameList.vue';

  export type IValue = {
    db_name: string;
    rename_cluster_list: number[];
    rename_db_name: string;
    target_db_name: string;
  };

  interface Props {
    data: {
      dstCluster: {
        id: number;
        master_domain: string;
      }[];
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  type Emits = (e: 'submit', data: typeof modelValue.value) => void;

  interface Exposes {
    updateTableKey(): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const modelValue = defineModel<{
    dbIgnoreName: string[];
    dbName: string[];
    renameInfoList: IValue[];
  }>({
    required: true,
  });
  const { t } = useI18n();

  const tableKey = ref(Date.now().toString());
  const dbNameMemo = _.cloneDeep(modelValue.value.dbName || []);

  const updateTableKey = () => {
    const hasEditDbRename = modelValue.value.dbName.some((item) => {
      return dbNameMemo.includes(item);
    });
    if (!hasEditDbRename) {
      return;
    }
    tableKey.value = Date.now().toString();
  };

  const handleSubmit = () => {
    emits('submit', modelValue.value);
    isShow.value = false;
  };

  const handleCancel = () => {
    isShow.value = false;
  };

  defineExpose<Exposes>({
    updateTableKey,
  });
</script>
<style lang="less" scoped>
  .edit-name-box {
    padding: 20px 24px;
  }
</style>
