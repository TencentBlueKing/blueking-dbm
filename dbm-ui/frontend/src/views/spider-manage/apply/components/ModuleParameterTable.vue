<template>
  <BkLoading :loading="isLoading">
    <ParameterTable
      ref="tableRef"
      :data="configData.conf_items"
      :is-anomalies="isAnomalies"
      level="module"
      :origin-data="originConfItems"
      :parameters="parameters"
      @add-item="handleAddConfItem"
      @on-change-enums="handleChangeEnums"
      @on-change-lock="handleChangeLock"
      @on-change-multiple-enums="handleChangeMultipleEnums"
      @on-change-number-input="handleChangeNumberInput"
      @on-change-parameter-item="handleChangeParameterItem"
      @on-change-range="handleChangeRange"
      @refresh="fetchLevelConfig"
      @remove-item="handleRemoveConfItem" />
  </BkLoading>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useRequest } from 'vue-request';

  import {
    getConfigNames,
    getLevelConfig,
    updateBusinessConfig,
  } from '@services/source/configs';
  import type { ConfigBaseDetails, ParameterConfigItem } from '@services/types/configs';

  import ParameterTable from '@views/db-configure/components/ParameterTable.vue';
  import {
    type DiffItem,
    useDiff,
  } from '@views/db-configure/hooks/useDiff';

  interface Props {
    bizId: number,
    version: string,
  }

  const props = defineProps<Props>();

  const tableRef = ref();
  const isLoading = ref(false);
  const isAnomalies = ref(false);
  const originConfItems = shallowRef<ParameterConfigItem[]>([]);
  const configData = ref<ConfigBaseDetails>({
    name: '',
    version: '',
    description: '',
    conf_items: [],
  });
  const paramsConfigDataStringify = ref('');

  const {
    data: parameters,
    run: fetchParameters,
  } = useRequest(getConfigNames, {
    manual: true,
  });

  watch(() => props.version, () => {
    if (props.version) {
      fetchParameters({
        meta_cluster_type: 'tendbcluster',
        conf_type: 'dbconf',
        version: props.version,
      });
      fetchLevelConfig();
    }
  }, { immediate: true });

  const fetchParams = computed(() => ({
    bk_biz_id: props.bizId,
    level_name: 'app',
    level_value: props.bizId,
    // level_name: isReadonly.value ? 'module' : 'app',
    // level_value: isReadonly.value ? moduleId.value : bizId.value,
    meta_cluster_type: 'tendbcluster',
    conf_type: 'dbconf',
    version: props.version,
  }));

  // 查询参数配置
  const fetchLevelConfig = () => {
    isLoading.value = true;

    // 若没有 module_id 则拉取业务配置，反之获取模块配置
    getLevelConfig(fetchParams.value)
      .then((res) => {
        configData.value = res;
        paramsConfigDataStringify.value = JSON.stringify(res.conf_items);

        // 备份 conf_items 用于 diff
        originConfItems.value = _.cloneDeep(res.conf_items);

        isAnomalies.value = false;
      })
      .catch(() => {
        configData.value = {
          name: '',
          version: '',
          description: '',
          conf_items: [],
        };
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  // 添加配置项
  const handleAddConfItem = (index: number) => {
    configData.value.conf_items.splice(index + 1, 0, {
      conf_name: '',
      conf_name_lc: '',
      description: '',
      flag_disable: 0,
      flag_locked: 0,
      need_restart: 0,
      value_allowed: '',
      value_default: '',
      value_type: '',
      value_type_sub: '',
      op_type: 'add',
    });
  };

  // 删除配置项
  const handleRemoveConfItem = (index: number) => {
    configData.value.conf_items.splice(index, 1);
  };

  // 将 number input 的值调整为 string 类型，否则 diff 会出现类型不一样
  const handleChangeNumberInput = (index: number, key: 'value_default' | 'conf_value', value: number) => {
    configData.value.conf_items[index][key] = String(value);
  };

  // 范围选择
  const handleChangeRange = (index: number,  { max, min }: { max: number, min: number }) => {
    configData.value.conf_items[index].value_allowed = (min || max) ? `[${min || 0},${max || 0}]` : '';
  };

  // multipleEnums 变更
  const handleChangeMultipleEnums = (index: number, _: string, value: string[]) => {
    configData.value.conf_items[index].value_default = value.join(',');
  };

  // enums 变更
  const handleChangeEnums = (index: number, value: string[]) => {
    configData.value.conf_items[index].value_allowed = value.join('|');
  };

  // 用于记录锁定前层级信息
  const lockLevelNameMap: Record<string, string | undefined> = {};

  // 变更锁定
  const handleChangeLock = (index: number, value: boolean) => {
    const lockedValue = Number(value);
    const isLocked = lockedValue === 1;
    const data = configData.value.conf_items[index];
    configData.value.conf_items[index].flag_locked = lockedValue;

    if (isLocked) {
      lockLevelNameMap[data.conf_name] = data.level_name;
    }
    // 锁定则将层级信息设置为当前层级，反之则恢复层级信息
    configData.value.conf_items[index].level_name = isLocked ? 'module' : lockLevelNameMap[data.conf_name];
  };

  // 选择参数项
  const handleChangeParameterItem = (index: number, selected: ParameterConfigItem) => {
    configData.value.conf_items[index] = Object.assign(_.cloneDeep(selected), { op_type: 'add' });
  };

  // 绑定参数配置
  const bindConfigParameters = (moduleName: string) => {
    const { data } = useDiff(configData.value.conf_items, originConfItems.value);
    const confItems = data.map((item: DiffItem) => {
      const type = item.status === 'delete' ? 'remove' : 'update';
      const data = item.status === 'delete' ?  item.before : item.after;
      return Object.assign(data, { op_type: type });
    });

    const params = {
      name: moduleName,
      conf_items: confItems,
      description: '',
      publish_description: '',
      confirm: 0,
      ...fetchParams.value,
    };
    return updateBusinessConfig(params);
  };

  const handleReset = () => {
    configData.value = {
      name: '',
      version: '',
      description: '',
      conf_items: [],
    };
    parameters.value = [];
    originConfItems.value = [];
  };

  defineExpose({
    bindConfigParameters,
    handleReset,
    validate: () => tableRef.value.validate(),
    hasChange: () => paramsConfigDataStringify.value !== JSON.stringify(configData.value.conf_items),
  });
</script>
