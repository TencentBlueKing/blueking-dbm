<template>
  <div class="sqlserver-manage-rename-info-box">
    <EditableTable
      ref="editableTable"
      :model="modelValue"
      :rules="rules">
      <EditableRow
        v-for="(item, index) in modelValue"
        :key="index">
        <EditableColumn :label="t('构造 DB 名称')">
          <EditableBlock v-model="item.db_name" />
        </EditableColumn>
        <EditableColumn
          ref="targetDbNameRef"
          :class="{
            'is-change': valueMemo[index].target_db_name !== item.target_db_name,
          }"
          field="target_db_name"
          :label="t('构造后 DB 名称（自动生成，可修改）')"
          @validate="(result: boolean) => handleTargetDbNameValidate(result, index)">
          <EditableInput
            v-model="item.target_db_name"
            @change="(value: string) => handleTargetDbChange(value, index)" />
        </EditableColumn>
        <EditableColumn
          :class="{
            'is-change': valueMemo[index].rename_db_name !== item.rename_db_name,
          }"
          field="rename_db_name"
          :label="t('已存在的 DB（可修改）')"
          @validate="(result: boolean) => handleRenameDbNameValidate(result, index)">
          <EditableInput
            v-model="item.rename_db_name"
            :disabled="!item.rename_db_name && !isTargetDbNameError[index]" />
        </EditableColumn>
      </EditableRow>
      <template
        v-if="modelValue.length < 1"
        #empty>
        <BkException
          description="没有数据"
          scene="part"
          type="empty" />
      </template>
    </EditableTable>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import { Column as EditableColumn } from '@components/editable-table/Index.vue';

  import type { IValue } from '../Index.vue';

  interface Props {
    targetClusterId: number;
  }

  interface Expose {
    getValue: () => Promise<boolean>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<IValue[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');
  const targetDbNameRef = useTemplateRef<Array<typeof EditableColumn>>('targetDbNameRef');

  const isTargetDbNameError = ref(Array.from({ length: modelValue.value.length }, () => false));
  const isRenameDbNameError = ref(Array.from({ length: modelValue.value.length }, () => false));

  const valueMemo = _.cloneDeep(modelValue.value);

  const rules = {
    rename_db_name: [
      {
        message: t('和其它已填写数据重复'),
        trigger: 'change',
        validator: (value: string, { rowIndex }: { rowIndex: number }) => {
          if (!value) {
            return true;
          }
          return _.every(modelValue.value, (item, index) => {
            if (index === rowIndex) {
              return item.target_db_name !== value;
            }
            return item.target_db_name !== value && item.rename_db_name !== value;
          });
        },
      },
      {
        message: t('跟已存在的 DB 名冲突，请修改其一'),
        trigger: 'change',
        validator: (value: string) => {
          if (!value) {
            return true;
          }
          return checkClusterDatabase({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_id: props.targetClusterId,
            db_list: [value],
          }).then((data) => !Object.values(data)[0]);
        },
      },
    ],
    target_db_name: [
      {
        message: t('构造后 DB 名称不能为空'),
        trigger: 'change',
        validator: (value: string) => Boolean(value),
      },
      {
        message: t('跟已存在的 DB 名冲突，请修改其一'),
        trigger: 'change',
        validator: (value: string, { rowIndex }: { rowIndex: number }) => {
          if (isNotNeedValidateTargetDb(rowIndex)) {
            return true;
          }
          return _.every(modelValue.value, (item, index) => {
            if (index === rowIndex) {
              return true;
            }
            return item.target_db_name !== value;
          });
        },
      },
      {
        message: t('跟已存在的 DB 名冲突，请修改其一'),
        trigger: 'change',
        validator: (value: string, { rowIndex }: { rowIndex: number }) => {
          if (isNotNeedValidateTargetDb(rowIndex)) {
            return true;
          }
          return checkClusterDatabase({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_id: props.targetClusterId,
            db_list: [value],
          }).then((data) => !Object.values(data)[0]);
        },
      },
    ],
  };

  // rename_db_name(第三列)可用时，不需要校验 target_db_name(第二列)
  const isNotNeedValidateTargetDb = (rowIndex: number) => {
    return modelValue.value[rowIndex].rename_db_name && !isRenameDbNameError.value[rowIndex];
  };

  const handleTargetDbChange = (value: string, index: number) => {
    modelValue.value[index].rename_db_name = '';
  };

  const handleTargetDbNameValidate = (result: boolean, index: number) => {
    isTargetDbNameError.value[index] = !result;
  };

  const handleRenameDbNameValidate = (result: boolean, index: number) => {
    isRenameDbNameError.value[index] = !result;
    targetDbNameRef.value![index].validate();
  };

  onMounted(() => {
    setTimeout(() => {
      targetDbNameRef.value!.forEach((item) => item.validate());
    });
  });

  defineExpose<Expose>({
    getValue() {
      return editableTableRef.value!.validate();
    },
  });
</script>
<style lang="less">
  .sqlserver-manage-rename-info-box {
    .is-change {
      background: #fff8e9;

      :deep(.table-edit-input) {
        background: inherit;

        .bk-input--text {
          background: inherit;
        }
      }
    }
  }
</style>
