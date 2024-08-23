<template>
  <tbody>
    <tr>
      <td>{{ localValue.db_name }}</td>
      <td
        :class="{
          'is-change': valueMemo['target_db_name'] !== localValue['target_db_name'],
        }"
        style="padding: 0">
        <TableEditInput
          ref="targetDbNameRef"
          :model-value="localValue.target_db_name"
          :rules="targetDbNamerules"
          @error="handleTargetDbNameError"
          @submit="handleTargetDbChange" />
      </td>
      <td
        :class="{
          'is-change': valueMemo['rename_db_name'] !== localValue['rename_db_name'],
        }"
        style="padding: 0">
        <TableEditInput
          ref="renameDbNameRef"
          :disabled="!localValue.rename_db_name && !isTargetDbNameError"
          :model-value="localValue.rename_db_name"
          :rules="renameDbNamerules"
          @error="handleRenameDbNameError"
          @submit="handleRenameDbChange" />
      </td>
    </tr>
  </tbody>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { onMounted, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import type { IValue } from '../../Index.vue';

  interface Props {
    targetClusterId: number;
    wholeDbList: IValue[];
    index: number;
  }

  interface Emits {
    (e: 'change', value: IValue): void;
  }

  interface Expose {
    getValue: () => Promise<IValue>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const valueMemo = _.clone(props.wholeDbList[props.index]);

  const targetDbNameRef = ref<InstanceType<typeof TableEditInput>>();
  const renameDbNameRef = ref<InstanceType<typeof TableEditInput>>();
  const localValue = ref(_.clone(props.wholeDbList[props.index]));
  const isTargetDbNameError = ref(false);
  const isRenameDbNameError = ref(false);

  // rename_db_name(第三列)可用时，不需要校验 target_db_name(第二列)
  const isNotNeedValidateTargetDb = computed(() => localValue.value.rename_db_name && !isRenameDbNameError.value);

  const targetDbNamerules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('构造后 DB 名称不能为空'),
    },
    {
      validator: (value: string) => {
        if (isNotNeedValidateTargetDb.value) {
          return true;
        }
        return _.every(props.wholeDbList, (item, index) => {
          if (index === props.index) {
            return true;
          }
          return item.target_db_name !== value;
        });
      },
      message: t('跟已存在的 DB 名冲突，请修改其一'),
    },
    {
      validator: (value: string) => {
        if (isNotNeedValidateTargetDb.value) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.targetClusterId,
          db_list: [value],
        }).then((data) => !Object.values(data)[0]);
      },
      message: t('跟已存在的 DB 名冲突，请修改其一'),
    },
  ];

  const renameDbNamerules = [
    {
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return _.every(props.wholeDbList, (item, index) => {
          if (index === props.index) {
            return item.target_db_name !== value;
          }
          return item.target_db_name !== value && item.rename_db_name !== value;
        });
      },
      message: t('和其它已填写数据重复'),
    },
    {
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
      message: t('跟已存在的 DB 名冲突，请修改其一'),
    },
  ];

  const handleTargetDbChange = (value: string) => {
    if (localValue.value.target_db_name === value) {
      return;
    }
    localValue.value.target_db_name = value;
    localValue.value.rename_db_name = '';
    emits('change', localValue.value);
  };

  const handleTargetDbNameError = (result: boolean) => {
    isTargetDbNameError.value = result;
  };

  const handleRenameDbChange = (value: string) => {
    localValue.value.rename_db_name = value;
    emits('change', localValue.value);
  };

  const handleRenameDbNameError = (result: boolean) => {
    isRenameDbNameError.value = result;
    targetDbNameRef.value!.validator().then((result) => {
      isTargetDbNameError.value = !result;
    });
  };

  onMounted(() => {
    targetDbNameRef.value!.validator().then((result) => {
      isTargetDbNameError.value = !result;
    });
  });

  defineExpose<Expose>({
    getValue() {
      return renameDbNameRef
        .value!.getValue()
        .then(() => targetDbNameRef.value!.getValue())
        .then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .is-change {
    background: #fff8e9;

    :deep(.table-edit-input) {
      background: inherit;

      .bk-input--text {
        background: inherit;
      }
    }
  }
</style>
