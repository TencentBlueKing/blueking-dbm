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
  <BkLoading
    :loading="state.loading"
    :z-index="30">
    <DbCard :title="$t('参数配置')">
      <template #header-right>
        <div class="diagrams">
          <div class="diagrams-item diagrams-item--create">
            <i class="diagrams-item-square" />
            <span class="diagrams-item-name">{{ $t('新增') }}</span>
          </div>
          <div class="diagrams-item diagrams-item--update">
            <i class="diagrams-item-square" />
            <span class="diagrams-item-name">{{ $t('更新') }}</span>
          </div>
        </div>
      </template>
      <ParameterTable
        ref="parameterTableRef"
        :data="state.data.conf_items"
        :is-anomalies="state.isAnomalies"
        :level="levelParams.level_name"
        :origin-data="state.originConfItems"
        :parameters="state.parameters"
        :sticky-top="28"
        @add-item="handleAddConfItem"
        @on-change-enums="handleChangeEnums"
        @on-change-lock="handleChangeLock"
        @on-change-multiple-enums="handleChangeMultipleEnums"
        @on-change-number-input="handleChangeNumberInput"
        @on-change-parameter-item="handleChangeParameterItem"
        @on-change-range="handleChangeRange"
        @refresh="fetchLevelConfig"
        @remove-item="handleRemoveConfItem" />
    </DbCard>
  </BkLoading>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getConfigBaseDetails, getConfigNames, getLevelConfig } from '@services/configs';
  import type { ConfigBaseDetails, ParameterConfigItem } from '@services/types/configs';

  import { useMainViewStore } from '@stores';

  import {
    confLevelInfos,
    ConfLevels,
    type ConfLevelValues,
  } from '@common/const';

  import { useLevelParams } from '../hooks/useLevelParams';

  import ParameterTable from './ParameterTable.vue';

  interface Props {
    level?: ConfLevelValues
  }

  interface Emits {
    (e: 'change', value: { data: ConfigBaseDetails, changed: boolean }): void
  }

  const props = withDefaults(defineProps<Props>(), {
    level: ConfLevels.PLAT,
  });

  /**
   * 表单数据变更
   */
  const emit = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();
  const mainViewStore = useMainViewStore();

  const state = reactive({
    loading: false,
    loadingParameter: false,
    isAnomalies: false,
    data: {
      name: '',
      version: '',
      description: '',
      conf_items: [],
    } as ConfigBaseDetails,
    parameters: [] as ParameterConfigItem[],
    originConfItems: [] as ParameterConfigItem[],
    cloneDataStringify: '',
  });
  // 是否为平台级别配置
  const isPlat = computed(() => props.level === ConfLevels.PLAT);

  // 请求参数
  const baseParams = computed(() => {
    const { clusterType, confType, version } = route.params;
    return {
      meta_cluster_type: clusterType as string,
      conf_type: confType as string,
      version: version as string,
    };
  });

  // 获取层级相关参数
  const levelParams = useLevelParams(isPlat.value);
  const fetchConfigParams = computed(() => ({
    ...levelParams.value,
    ...baseParams.value,
  }));

  // 查询详情 api
  const fetchConfigDetails = computed(() => (isPlat.value ? getConfigBaseDetails : getLevelConfig));
  // 当前层级 tag
  const tagText = computed(() => confLevelInfos[props.level].tagText);

  /**
   * 查询业务配置详情
   */
  fetchLevelConfig();

  function fetchLevelConfig() {
    state.loading = true;
    fetchConfigDetails.value(fetchConfigParams.value)
      .then((res) => {
        state.data = res;
        state.cloneDataStringify = JSON.stringify(res);

        // 设置面包屑信息
        mainViewStore.breadCrumbsTitle = t('编辑【xx】', [res.name]);
        mainViewStore.tags = [{
          theme: 'info',
          text: tagText.value,
        }];

        // 备份 conf_items 用于 diff
        state.originConfItems = _.cloneDeep(res.conf_items);

        state.isAnomalies = false;
      })
      .catch(() => {
        state.data = {
          name: '',
          version: '',
          description: '',
          conf_items: [],
        };
        state.isAnomalies = true;
      })
      .finally(() => {
        state.loading = false;
      });
  }

  /**
   * 查询配置项名称列表
   */
  const fetchConfigNames = () => {
    state.loadingParameter = true;
    getConfigNames(baseParams.value)
      .then((res) => {
        state.parameters = res;
      })
      .finally(() => {
        state.loadingParameter = false;
      });
  };
  fetchConfigNames();

  /**
   * 校验参数配置
   */
  const parameterTableRef = ref();
  const validate = async ()  => {
    const parameterValidate = await parameterTableRef.value.validate()
      .then(() => true)
      .catch(() => false);
    return parameterValidate;
  };

  watch(() => state.data, (value) => {
    const isChange = state.cloneDataStringify !== JSON.stringify(value);
    emit('change', {
      data: value,
      changed: isChange,
    });
  }, { deep: true });

  /**
   * 返回 diff 数据参数
   */
  const getData = () => ({
    data: state.data,
    origin: state.originConfItems,
  });

  defineExpose({ validate, getData });

  // 添加配置项
  const handleAddConfItem = (index: number) => {
    state.data.conf_items.splice(index + 1, 0, {
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
    state.data.conf_items.splice(index, 1);
  };

  // 将 number input 的值调整为 string 类型，否则 diff 会出现类型不一样
  const handleChangeNumberInput = (index: number, key: 'value_default' | 'conf_value', value: number) => {
    state.data.conf_items[index][key] = String(value);
  };

  // 范围选择
  const handleChangeRange = (index: number,  { max, min }: { max: number, min: number }) => {
    state.data.conf_items[index].value_allowed = (min || max) ? `[${min || 0},${max || 0}]` : '';
  };

  // multipleEnums 变更
  const handleChangeMultipleEnums = (index: number, _: string, value: string[]) => {
    state.data.conf_items[index].value_default = value.join(',');
  };

  // enums 变更
  const handleChangeEnums = (index: number, value: string[]) => {
    state.data.conf_items[index].value_allowed = value.join('|');
  };

  // 用于记录锁定前层级信息
  const lockLevelNameMap: Record<string, string | undefined> = {};

  // 变更锁定
  const handleChangeLock = (index: number, value: boolean) => {
    const lockedValue = Number(value);
    const isLocked = lockedValue === 1;
    const data = state.data.conf_items[index];
    state.data.conf_items[index].flag_locked = lockedValue;

    if (isPlat.value === false) {
      // 锁定前记录层级信息
      if (isLocked) {
        lockLevelNameMap[data.conf_name] = data.level_name;
      }
      // 锁定则将层级信息设置为当前层级，反之则恢复层级信息
      state.data.conf_items[index].level_name = isLocked ? props.level : lockLevelNameMap[data.conf_name];
    }
  };

  // 选择参数项
  const handleChangeParameterItem = (index: number, selected: ParameterConfigItem) => {
    state.data.conf_items[index] = Object.assign(_.cloneDeep(selected), { op_type: 'add' });
  };
</script>

<style lang="less" scoped>
  .base-form {
    max-width: 654px;
  }

  .tips {
    color: @default-color;

    .db-icon-attention {
      margin-right: 4px;
      font-size: @font-size-normal;
    }
  }

  .diagrams {
    display: flex;
    align-items: center;

    &-item {
      display: flex;
      align-items: center;
      margin-left: 8px;
    }

    &-item-square {
      width: 12px;
      height: 12px;
      border: 1px solid transparent;
    }

    &-item-name {
      padding: 0 6px;
    }

    &-item--create {
      .diagrams-item-square {
        background-color: #f2fff4;
        border-color: #b3ffc1;
      }
    }

    &-item--update {
      .diagrams-item-square {
        background-color: #fff4e2;
        border-color: #ffdfac;
      }
    }
  }
</style>
