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
        ref="clusterDb"
        v-model="localValue"
        :data="data" />
      <div style="margin-top: 24px; margin-bottom: 16px; font-size: 12px">
        <span style="font-weight: bold; color: #313238">{{ t('DB 列表') }}</span>
        <I18nT
          keypath="（共 n 个）"
          style="color: #63656e">
          {{ localValue.renameInfoList.length }}
        </I18nT>
        <ImportBtn
          v-model="localValue"
          class="ml-12"
          :data="data" />
        <ExportBtn
          v-model="localValue"
          class="ml-12"
          :data="data" />
      </div>
      <RenameList
        ref="renameList"
        v-model="localValue"
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
  import { useI18n } from 'vue-i18n';

  import { messageError } from '@utils';

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
    };
    dbConflict: boolean;
  }

  type Emits = (e: 'submit', data: Pick<Props['data'], 'dbIgnoreName' | 'dbName' | 'renameInfoList'>) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const clusterDbRef = useTemplateRef<InstanceType<typeof ClusterDb>>('clusterDb');
  const renameListRef = useTemplateRef<InstanceType<typeof RenameList>>('renameList');
  const localValue = ref<{
    dbIgnoreName: string[];
    dbName: string[];
    renameInfoList: IValue[];
  }>({
    dbIgnoreName: [],
    dbName: [],
    renameInfoList: [],
  });

  const handleSubmit = async () => {
    try {
      const renameValid = await renameListRef.value?.validate();
      if (!renameValid) {
        throw new Error();
      }
      emits('submit', localValue.value);
    } catch {
      messageError(t('请修改冲突的 DB 名'));
    }
  };

  const handleCancel = () => {
    isShow.value = false;
  };

  watch(isShow, () => {
    if (isShow.value && props.dbConflict) {
      localValue.value = {
        dbIgnoreName: props.data.dbIgnoreName,
        dbName: props.data.dbName,
        renameInfoList: props.data.renameInfoList,
      };
      setTimeout(() => {
        clusterDbRef.value?.fetchData();
      });
    }
  });
</script>
<style lang="less" scoped>
  .edit-name-box {
    padding: 20px 24px;
  }
</style>
