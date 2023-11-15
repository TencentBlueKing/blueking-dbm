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
  <DbForm
    ref="createModuleFormRef"
    class="create-module db-scroll-y"
    :label-width="168"
    :model="formData">
    <DbCard
      class="mb-16"
      :title="$t('模块信息')">
      <BkFormItem
        :label="$t('模块名称')"
        property="module_name"
        required
        :rules="rules.module_name">
        <BkInput
          v-model="formData.module_name"
          :placeholder="$t('由英文字母_数字_连字符_组成')"
          :readonly="isReadonly" />
        <span class="belong-business">{{ $t('所属业务') }} : {{ bizInfo.name }}</span>
      </BkFormItem>
    </DbCard>
    <DbCard
      class="mb-16"
      :title="$t('绑定数据库配置')">
      <BkFormItem
        :label="$t('数据库类型')"
        property="mysql_type"
        required>
        <BkTag
          class="mysql-type-item"
          theme="info"
          type="stroke">
          <template #icon>
            <i class="db-icon-mysql mr-5" />
          </template>
          {{ ticketInfo.name }}
        </BkTag>
      </BkFormItem>
      <BkFormItem
        :label="$t('数据库版本')"
        property="version"
        required>
        <BkSelect
          v-model="formData.version"
          :clearable="false"
          :disabled="isBindSuccessfully"
          filterable
          :input-search="false"
          :loading="loadingState.versions"
          :placeholder="$t('请选择数据库版本')">
          <BkOption
            v-for="(item, index) in listState.versions"
            :key="index"
            :label="item"
            :value="item" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="$t('字符集')"
        property="character_set"
        required>
        <BkSelect
          v-model="formData.character_set"
          :clearable="false"
          :disabled="isBindSuccessfully"
          filterable
          :placeholder="$t('请选择字符集')">
          <BkOption
            v-for="(item, index) in listState.characterSets"
            :key="index"
            :label="item"
            :value="item" />
        </BkSelect>
      </BkFormItem>
    </DbCard>
    <DbCard :title="$t('参数配置')">
      <BkLoading :loading="configState.loading">
        <ParameterTable
          ref="parameterTableRef"
          :data="configState.data.conf_items"
          :is-anomalies="configState.isAnomalies"
          level="module"
          :origin-data="configState.originConfItems"
          :parameters="configState.parameters"
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
    </DbCard>
    <div class="staff-setting__footer">
      <div class="absolute-footer">
        <BkButton
          :disabled="disabledSubmit"
          :loading="loadingState.submit"
          theme="primary"
          @click="handleSubmit">
          {{ $t('保存') }}
        </BkButton>
        <BkButton
          :disabled="loadingState.submit"
          @click="resetFormData()">
          {{ $t('重置') }}
        </BkButton>
      </div>
    </div>
  </DbForm>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { createModules } from '@services/source/cmdb';
  import {
    getConfigNames,
    getLevelConfig,
    saveModulesDeployInfo,
    updateBusinessConfig,
  } from '@services/source/configs';
  import { getVersions } from '@services/source/version';
  import type { ConfigBaseDetails, ParameterConfigItem } from '@services/types/configs';

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    mysqlType,
    type MysqlTypeString,
  } from '@common/const';

  import ParameterTable from '@views/db-configure/components/ParameterTable.vue';
  import {
    type DiffItem,
    useDiff,
  } from '@views/db-configure/hooks/useDiff';
  const { t } = useI18n();

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const isBindSuccessfully = ref(false);
  const paramsConfigDataStringify = ref('');
  const disabledSubmit = computed(() => {
    if (isBindSuccessfully.value === false) return false;
    return paramsConfigDataStringify.value === JSON.stringify(configState.data.conf_items);
  });
  // 数据库类型信息
  const ticketType = computed(() => route.params.type as MysqlTypeString);
  const ticketInfo = computed(() => mysqlType[ticketType.value]);
  // 业务信息
  const bizId = computed(() => Number(route.params.bk_biz_id));
  const bizInfo = computed(() => globalBizsStore.bizs.find(info => info.bk_biz_id ===  bizId.value) || { name: '' });
  // 模块信息
  const moduleId =  ref(Number(route.params.db_module_id) ?? '');
  const isNewModule = computed(() => !route.params.db_module_id);
  const isReadonly = computed(() => (isNewModule.value ? !!moduleId.value : true));

  const formData = reactive(getFormData());
  const listState = reactive({
    versions: [] as string[],
    characterSets: ['utf8', 'utf8mb4', 'gbk', 'latin1'],
  });
  const loadingState = reactive({
    versions: false,
    submit: false,
  });
  const rules = {
    module_name: [
      {
        required: true,
        message: t('模块名称不能为空'),
        trigger: 'blur',
      },
      {
        pattern: /^[0-9a-zA-Z-]+$/,
        message: t('由英文字母_数字_连字符_组成'),
        trigger: 'blur',
      },
    ],
  };

  /**
   * 获取表单基础信息
   */
  function getFormData() {
    return {
      module_name: (route.query.module_name ?? '') as string,
      mysql_type: ticketType.value,
      version: '',
      character_set: '',
    };
  }

  /**
   * 获取版本列表
   */
  function fetchVersions() {
    loadingState.versions = true;
    getVersions({ query_key: ticketInfo.value.type, db_type: 'mysql' })
      .then((res) => {
        listState.versions = res;
      })
      .finally(() => {
        loadingState.versions = false;
      });
  }
  fetchVersions();

  const createModuleFormRef = ref();
  const parameterTableRef = ref();
  /**
   * 提交表单
   */
  async function handleSubmit() {
    loadingState.submit = true;
    try {
      // 校验表单信息
      await Promise.all([
        createModuleFormRef.value?.validate(),
        parameterTableRef.value?.validate(),
      ]);

      // 新建模块或已经新建成功则不执行创建
      if (!isReadonly.value) {
        await newModule();
      }

      // 绑定模块数据库配置
      await bindModulesDeployInfo();

      // 绑定参数配置
      await bindConfigParameters();

      Message({
        message: isNewModule.value ? t('创建DB模块并绑定数据库配置成功') : t('绑定配置成功'),
        theme: 'success',
      });
      window.changeConfirm = false;
      router.go(-1);
    } catch (e) {
      console.log(e);
    }
    loadingState.submit = false;
  }

  /**
   * 创建模块
   */
  function newModule() {
    const params = {
      id: bizId.value,
      db_module_name: formData.module_name,
      cluster_type: ticketInfo.value.type,
    };

    return createModules(params)
      .then((res) => {
        moduleId.value = res.db_module_id;
      });
  }

  /**
   * 绑定数据库配置
   */
  function bindModulesDeployInfo() {
    const params = {
      level_name: 'module',
      version: 'deploy_info',
      conf_type: 'deploy',
      bk_biz_id: bizId.value,
      level_value: moduleId.value,
      meta_cluster_type: ticketInfo.value.type,
      conf_items: [
        {
          conf_name: 'charset',
          conf_value: formData.character_set,
          op_type: 'update',
          description: t('字符集'),
        },
        {
          conf_name: 'db_version',
          conf_value: formData.version,
          op_type: 'update',
          description: t('数据库版本'),
        },
      ],
    };
    return saveModulesDeployInfo(params)
      .then(() => {
        isBindSuccessfully.value = true;
      });
  }

  function resetFormData() {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        const resetData = isNewModule.value ? getFormData() : { version: '', character_set: '' };
        _.merge(formData, resetData);
        configState.data = {
          name: '',
          version: '',
          description: '',
          conf_items: [],
        };
        configState.parameters = [];
        configState.originConfItems = [];
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }

  const configState = reactive({
    loading: false,
    isAnomalies: false,
    data: {
      name: '',
      version: '',
      description: '',
      conf_items: [],
    } as ConfigBaseDetails,
    parameters: [] as ParameterConfigItem[],
    originConfItems: [] as ParameterConfigItem[],
  });
  const fetchParams = computed(() => ({
    bk_biz_id: bizId.value,
    level_name: isReadonly.value ? 'module' : 'app',
    level_value: isReadonly.value ? moduleId.value : bizId.value,
    meta_cluster_type: ticketInfo.value.type,
    conf_type: 'dbconf',
    version: formData.version,
  }));

  /**
   * 查询参数配置
   */
  function fetchLevelConfig() {
    configState.loading = true;

    // 若没有 module_id 则拉取业务配置，反之获取模块配置
    getLevelConfig(fetchParams.value)
      .then((res) => {
        configState.data = res;
        paramsConfigDataStringify.value = JSON.stringify(res.conf_items);

        // 备份 conf_items 用于 diff
        configState.originConfItems = _.cloneDeep(res.conf_items);

        configState.isAnomalies = false;
      })
      .catch(() => {
        configState.data = {
          name: '',
          version: '',
          description: '',
          conf_items: [],
        };
        configState.isAnomalies = true;
      })
      .finally(() => {
        configState.loading = false;
      });
  }

  /**
   * 查询配置项名称列表
   */
  function fetchConfigNames() {
    getConfigNames({
      meta_cluster_type: ticketInfo.value.type,
      conf_type: 'dbconf',
      version: formData.version,
    })
      .then((res) => {
        configState.parameters = res;
      });
  }

  watch(() => formData.version, (version) => {
    if (version) {
      fetchConfigNames();
      fetchLevelConfig();
    }
  }, { immediate: true });

  /**
   * 绑定参数配置
   */
  function bindConfigParameters() {
    // 获取 conf_items
    const { data } = useDiff(configState.data.conf_items, configState.originConfItems);
    const confItems = data.map((item: DiffItem) => {
      const type = item.status === 'delete' ? 'remove' : 'update';
      const data = item.status === 'delete' ?  item.before : item.after;
      return Object.assign(data, { op_type: type });
    });

    const params = {
      name: formData.module_name,
      conf_items: confItems,
      description: '',
      publish_description: '',
      confirm: 0,
      ...fetchParams.value,
    };
    return updateBusinessConfig(params);
  }

  // 添加配置项
  const handleAddConfItem = (index: number) => {
    configState.data.conf_items.splice(index + 1, 0, {
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
    configState.data.conf_items.splice(index, 1);
  };

  // 将 number input 的值调整为 string 类型，否则 diff 会出现类型不一样
  const handleChangeNumberInput = (index: number, key: 'value_default' | 'conf_value', value: number) => {
    configState.data.conf_items[index][key] = String(value);
  };

  // 范围选择
  const handleChangeRange = (index: number,  { max, min }: { max: number, min: number }) => {
    configState.data.conf_items[index].value_allowed = (min || max) ? `[${min || 0},${max || 0}]` : '';
  };

  // multipleEnums 变更
  const handleChangeMultipleEnums = (index: number, _: string, value: string[]) => {
    configState.data.conf_items[index].value_default = value.join(',');
  };

  // enums 变更
  const handleChangeEnums = (index: number, value: string[]) => {
    configState.data.conf_items[index].value_allowed = value.join('|');
  };

  // 用于记录锁定前层级信息
  const lockLevelNameMap: Record<string, string | undefined> = {};

  // 变更锁定
  const handleChangeLock = (index: number, value: boolean) => {
    const lockedValue = Number(value);
    const isLocked = lockedValue === 1;
    const data = configState.data.conf_items[index];
    configState.data.conf_items[index].flag_locked = lockedValue;

    // if (isPlat.value === false) {
    // 锁定前记录层级信息
    if (isLocked) {
      lockLevelNameMap[data.conf_name] = data.level_name;
    }
    // 锁定则将层级信息设置为当前层级，反之则恢复层级信息
    configState.data.conf_items[index].level_name = isLocked ? 'module' : lockLevelNameMap[data.conf_name];
    // }
  };

  // 选择参数项
  const handleChangeParameterItem = (index: number, selected: ParameterConfigItem) => {
    configState.data.conf_items[index] = Object.assign(_.cloneDeep(selected), { op_type: 'add' });
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins";

  .create-module-loading {
    height: 100%;
  }

  .create-module {
    height: 100%;

    :deep(.bk-form-item) {
      max-width: 690px;
    }

    .db-card {
      &:last-child {
        margin-bottom: 0;
      }

      .belong-business {
        position: absolute;
        min-width: 400px;
        padding: 0 13px;
        font-size: 12px;
      }

      .mysql-type-item {
        height: 30px;
        color: @primary-color;
        background: white;
        border: 1px solid @border-primary;
      }
    }

    &__footer {
      margin-left: 192px;

      .bk-button {
        width: 88px;
      }
    }
  }
</style>
