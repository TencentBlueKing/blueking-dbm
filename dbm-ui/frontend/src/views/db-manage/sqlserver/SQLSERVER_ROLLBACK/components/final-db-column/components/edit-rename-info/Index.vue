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
  <DbSideslider
    v-model:is-show="isShow"
    :width="960">
    <template #header>
      <span>{{ t('恢复后库名') }}</span>
      <BkTag class="ml-8">{{ data.srcCluster.master_domain }}</BkTag>
    </template>
    <div class="edit-name-box">
      <ClusterDb
        v-model="localValue"
        :data="data" />
      <div style="margin-top: 24px; margin-bottom: 16px; font-size: 12px">
        <span style="font-weight: bold; color: #313238">{{ t('库名映射') }}</span>
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
        ref="renameListRef"
        v-model="localValue"
        :data="data" />
    </div>
    <template #footer>
      <BkButton
        class="w-88 mr-8"
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { messageError } from '@utils';

  import ClusterDb from './components/ClusterDb.vue';
  import ExportBtn from './components/ExportBtn.vue';
  import ImportBtn from './components/ImportBtn.vue';
  import RenameList from './components/RenameList.vue';

  export type IValue = {
    db_name: string;
    rename_db_name: string;
    target_db_name: string;
  };

  interface Props {
    data: {
      backupDbList?: string[];
      dbIgnoreName: string[];
      dbName: string[];
      renameInfoList: IValue[];
      srcCluster: {
        id: number;
        master_domain: string;
      };
      targetCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  type Emits = (e: 'submit', data: Pick<Props['data'], 'dbIgnoreName' | 'dbName' | 'renameInfoList'>) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const renameListRef = useTemplateRef<InstanceType<typeof RenameList>>('renameListRef');
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
      return Promise.reject();
    }
  };

  const handleClose = () => {
    isShow.value = false;
  };

  watch(isShow, () => {
    if (isShow.value) {
      localValue.value = {
        dbIgnoreName: _.cloneDeep(props.data.dbIgnoreName),
        dbName: _.cloneDeep(props.data.dbName),
        renameInfoList: _.cloneDeep(props.data.renameInfoList),
      };
    }
  });
</script>
<style lang="less" scoped>
  .edit-name-box {
    padding: 20px 24px;
  }
</style>
