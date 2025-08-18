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
  <div class="mysql-execute-objects">
    <DbFormItem
      ref="formItemRef"
      :label="t('变更内容')"
      property="execute_objects"
      required
      :rules="rules">
      <BkButton
        v-bk-tooltips="{
          content: t('请先选择目标集群'),
          disabled: clusterIds.length > 0,
        }"
        :disabled="clusterIds.length === 0"
        @click="handleShowSideSlider">
        <DbIcon
          class="mr-4"
          type="add" />
        <span>{{ t('添加') }}</span>
      </BkButton>
      <BkTable
        v-if="modelValue.length > 0"
        :key="renderKey"
        class="mt-16"
        :data="modelValue">
        <BkTableColumn
          field="dbnames"
          :label="t('变更 DB')"
          :min-width="200">
          <template #default="{ data }: {data: ExcuteObject}">
            <TagBlock :data="data.dbnames" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="ignore_dbnames"
          :label="t('忽略 DB')"
          :min-width="200">
          <template #default="{ data }: {data: ExcuteObject}">
            <TagBlock :data="data.ignore_dbnames" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="sql_files"
          :label="t('执行的 SQL')"
          width="300">
          <template #default="{ data, rowIndex }: {data: ExcuteObject, rowIndex: number}">
            <BkButton
              v-if="data.sql_files"
              text
              theme="primary"
              @click="() => handleTableEdit(data, rowIndex)">
              <template v-if="data.sql_files.length < 2">
                <DbIcon
                  style="margin-right: 4px; color: #3a84ff"
                  type="file" />
                {{ getSQLFilename(data.sql_files[0]) }}
              </template>
              <template v-else>
                {{ t('n 个 SQL 文件', { n: data.sql_files.length }) }}
              </template>
            </BkButton>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field=""
          :label="t('操作')"
          width="100">
          <template #default="{ data, rowIndex }: {data: ExcuteObject, rowIndex: number}">
            <BkButton
              text
              theme="primary"
              @click="() => handleTableEdit(data, rowIndex)">
              {{ t('编辑') }}
            </BkButton>
            <BkButton
              class="ml-12"
              text
              theme="primary"
              @click="() => handleTableDelete(rowIndex)">
              {{ t('删除') }}
            </BkButton>
          </template>
        </BkTableColumn>
      </BkTable>
    </DbFormItem>
    <DbSideslider
      v-model:is-show="isShowSideSlider"
      :disabled-confirm="disabledConfirm"
      :title="t('变更内容')"
      width="960"
      @shown="handleShown">
      <Content
        ref="contentRef"
        v-model:disabled-confirm="disabledConfirm"
        :all-dbnames="allDbnames"
        :cluster-version-list="clusterVersionList"
        :data="currentData"
        @change="handleChange" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import GrammarCheckModel from '@services/model/sql-import/grammar-check';
  import { type Mysql } from '@services/model/ticket/ticket';

  import { useSqlImport } from '@stores';

  import { DBTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import SqlFileModel from '@views/db-manage/common/mysql-sql-execute/model/SqlFile';

  import { getSQLFilename } from '@utils';

  import Content from './components/Content.vue';

  interface ExcuteObject {
    dbnames: string[];
    ignore_dbnames: string[];
    import_mode: 'manual' | 'file';
    sql_files: string[];
  }

  interface Props {
    clusterIds: number[];
    uploadFilePath: string;
  }

  interface Exposes {
    setReEditValue: (data: Mysql.ImportSqlFile['execute_objects']) => void;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<ExcuteObject[]>({
    required: true,
  });
  const clusterVersionList = defineModel<string[]>('clusterVersionList', {
    default: () => [],
  });

  const { t } = useI18n();
  const { updateDbType, updateUploadFilePath } = useSqlImport();

  updateDbType(DBTypes.MYSQL);

  let sqlFileCache = [] as Record<string, SqlFileModel>[];

  const rules = [
    {
      message: t('变更内容不能为空'),
      trigger: 'change',
      validator: (value: ExcuteObject[]) => value.length > 0,
    },
  ];

  const formItemRef = useTemplateRef('formItemRef');
  const contentRef = useTemplateRef('contentRef');

  const isShowSideSlider = ref(false);
  const disabledConfirm = ref(true);
  const currentIndex = ref(-1);
  const renderKey = ref(1);

  const currentData = shallowRef();

  const allDbnames = computed(() =>
    modelValue.value.filter((_item, index) => index !== currentIndex.value).flatMap((item) => item.dbnames),
  );

  const handleChange = ({
    rowData,
    sqlFileData,
  }: {
    rowData: ExcuteObject;
    sqlFileData: Record<string, SqlFileModel>;
  }) => {
    if (currentIndex.value > -1) {
      modelValue.value[currentIndex.value] = rowData;
      renderKey.value = renderKey.value + 1;
      sqlFileCache.splice(currentIndex.value, 1, sqlFileData);
    } else {
      modelValue.value = modelValue.value.concat(rowData);
      sqlFileCache = sqlFileCache.concat(sqlFileData);
    }
  };

  const handleTableEdit = (data: ExcuteObject, index: number) => {
    currentData.value = _.cloneDeep(data);
    currentIndex.value = index;
    isShowSideSlider.value = true;
  };

  const handleShown = () => {
    if (currentIndex.value > -1) {
      nextTick(() => {
        contentRef.value!.setInit(_.cloneDeep(sqlFileCache[currentIndex.value]));
      });
    }
  };

  const handleTableDelete = (index: number) => {
    modelValue.value.splice(index, 1);
    sqlFileCache.splice(index, 1);
    formItemRef.value!.clearValidate();
  };

  watch(
    () => props.uploadFilePath,
    () => {
      updateUploadFilePath(props.uploadFilePath);
    },
    {
      immediate: true,
    },
  );

  const handleShowSideSlider = () => {
    currentData.value = undefined;
    currentIndex.value = -1;
    isShowSideSlider.value = true;
  };

  defineExpose<Exposes>({
    setReEditValue(data: Mysql.ImportSqlFile['execute_objects']) {
      sqlFileCache = data.reduce<Record<string, SqlFileModel>[]>((prev, dataItem) => {
        const sqlFileInfo = dataItem.sql_files.reduce<Record<string, SqlFileModel>>((prev, sqlFileName) => {
          const localFileName = getSQLFilename(sqlFileName);
          const sqlFile = new SqlFileModel();
          sqlFile.grammarCheckStart();
          sqlFile.grammarCheckSuccessed({ [localFileName]: new GrammarCheckModel() });
          return Object.assign(prev, { [localFileName]: sqlFile });
        }, {});
        return prev.concat(sqlFileInfo);
      }, []);
    },
  });
</script>
<style lang="less">
  .mysql-execute-objects {
    display: block;
    margin-top: 16px;
    margin-bottom: 24px;

    .cluster-checking {
      height: 86px;
    }
  }
</style>
