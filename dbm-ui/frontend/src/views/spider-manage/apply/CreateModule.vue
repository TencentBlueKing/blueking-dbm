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
    ref="formRef"
    class="create-module db-scroll-y"
    :label-width="168"
    :model="formdata">
    <DbCard
      class="mb-16"
      :title="$t('模块信息')">
      <BkFormItem
        :label="$t('模块名称')"
        property="module_name"
        required
        :rules="rules.module_name">
        <BkInput
          v-model="formdata.module_name"
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
        required>
        <BkTag
          class="mysql-type-item"
          theme="info"
          type="stroke">
          <template #icon>
            <i class="db-icon-mysql mr-5" />
          </template>
          TenDBCluster
        </BkTag>
      </BkFormItem>
      <BkFormItem
        :label="$t('数据库版本')"
        property="version"
        required>
        <BkSelect
          v-model="formdata.version"
          :clearable="false"
          :disabled="isBindSuccessfully"
          filterable
          :input-search="false"
          :loading="isLoadVersions"
          :placeholder="$t('请选择数据库版本')">
          <BkOption
            v-for="(item, index) in versions"
            :key="index"
            :label="item"
            :value="item" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="$t('Spider版本')"
        property="spider_version"
        required>
        <BkSelect
          v-model="formdata.spider_version"
          :clearable="false"
          :disabled="isBindSuccessfully"
          filterable
          :input-search="false"
          :loading="isLoadSpiderVersions"
          :placeholder="$t('请选择xx', [$t('Spider版本')])">
          <BkOption
            v-for="(item, index) in spiderVersions"
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
          v-model="formdata.character_set"
          :clearable="false"
          :disabled="isBindSuccessfully"
          filterable
          :list="characterSets"
          :placeholder="$t('请选择字符集')" />
      </BkFormItem>
    </DbCard>
    <DbCard :title="$t('参数配置')">
      <BkRadioGroup
        v-model="clusterType"
        class="mb-12"
        type="capsule">
        <BkRadioButton
          label="tendbcluster"
          style="width: 200px;">
          {{ $t('MySQL参数配置') }}
        </BkRadioButton>
        <BkRadioButton
          label="spider"
          style="width: 200px;">
          {{ $t('Spider参数配置') }}
        </BkRadioButton>
      </BkRadioGroup>
      <ModuleParameterTable
        v-show="clusterType === 'tendbcluster'"
        ref="mysqlTableRef"
        :biz-id="bizId"
        :version="formdata.version" />
      <ModuleParameterTable
        v-show="clusterType === 'spider'"
        ref="spiderTableRef"
        :biz-id="bizId"
        :version="formdata.spider_version" />
    </DbCard>
    <div class="absolute-footer">
      <BkButton
        :disabled="disabledSubmit"
        :loading="isSubmintting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('保存') }}
      </BkButton>
      <BkButton
        :disabled="isSubmintting"
        @click="handleReset()">
        {{ $t('重置') }}
      </BkButton>
    </div>
  </DbForm>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  // TODO INTERFACE done
  // import { createModules, saveModulesDeployInfo } from '@services/ticket';
  import { createModules } from '@services/source/cmdb';
  import { saveModulesDeployInfo } from '@services/source/configs';
  import { getVersions } from '@services/versionFiles';

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import ModuleParameterTable from './components/ModuleParameterTable.vue';

  import { messageError } from '@/utils';

  const getFormData = () => ({
    module_name: (route.query.module_name ?? '') as string,
    version: '',
    spider_version: '',
    character_set: '',
  });

  const { t } = useI18n();

  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const mysqlTableRef = ref();
  const spiderTableRef = ref();
  const isBindSuccessfully = ref(false);
  const disabledSubmit = computed(() => {
    if (isBindSuccessfully.value === false) return false;
    return !mysqlTableRef.value?.hasChange?.() && !spiderTableRef.value?.hasChange?.();
  });
  // 业务信息
  const bizId = computed(() => Number(route.params.bizId));
  const bizInfo = computed(() => globalBizsStore.bizs.find(info => info.bk_biz_id ===  bizId.value) || { name: '' });
  // 模块信息
  const moduleId =  ref(Number(route.params.db_module_id) ?? '');
  const isNewModule = computed(() => !route.params.db_module_id);
  const isReadonly = computed(() => (isNewModule.value ? !!moduleId.value : true));

  const formRef = ref();
  const formdata = reactive(getFormData());
  const clusterType = ref('tendbcluster');
  const isSubmintting = ref(false);
  const characterSets = [
    {
      label: 'utf8',
      value: 'utf8',
    },
    {
      label: 'utf8mb4',
      value: 'utf8mb4',
    },
    {
      label: 'gbk',
      value: 'gbk',
    },
    {
      label: 'latin1',
      value: 'latin1',
    },
  ];
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

  // mysql versions
  const {
    data: versions,
    loading: isLoadVersions,
  } = useRequest(getVersions, {
    defaultParams: [
      {
        query_key: 'tendbcluster',
        db_type: 'mysql',
      },
    ],
  });

  // spider versions
  const {
    data: spiderVersions,
    loading: isLoadSpiderVersions,
  } = useRequest(getVersions, {
    defaultParams: [
      {
        query_key: 'spider',
        db_type: 'mysql',
      },
    ],
  });

  // 创建模块
  const newModule = () => {
    const params = {
      id: bizId.value,
      db_module_name: formdata.module_name,
      cluster_type: 'tendbcluster',
    };

    return createModules(params)
      .then((res) => {
        moduleId.value = res.db_module_id;
      });
  };

  // 绑定数据库配置
  const bindModulesDeployInfo = () => {
    const params = {
      level_name: 'module',
      version: 'deploy_info',
      conf_type: 'deploy',
      bk_biz_id: bizId.value,
      level_value: moduleId.value,
      meta_cluster_type: 'tendbcluster',
      conf_items: [
        {
          conf_name: 'charset',
          conf_value: formdata.character_set,
          op_type: 'update',
          description: t('字符集'),
        },
        {
          conf_name: 'db_version',
          conf_value: formdata.version,
          op_type: 'update',
          description: t('数据库版本'),
        },
        {
          conf_name: 'spider_version',
          conf_value: formdata.spider_version,
          op_type: 'update',
          description: t('Spider版本'),
        },
      ],
    };
    return saveModulesDeployInfo(params)
      .then(() => {
        isBindSuccessfully.value = true;
      });
  };

  /**
   * 提交表单
   */
  const handleSubmit = async () => {
    isSubmintting.value = true;

    try {
      // 校验表单信息
      await Promise.all([
        formRef.value.validate(),
        mysqlTableRef.value.validate()
          .catch((e: any) => {
            messageError(t('请确保MySQL参数配置填写正确'));
            return Promise.reject(e);
          }),
        spiderTableRef.value.validate()
          .catch((e: any) => {
            nextTick(() => {
              messageError(t('请确保Spider参数配置填写正确'));
            });
            return Promise.reject(e);
          }),
      ]);

      // 新建模块或已经新建成功则不执行创建
      if (!isReadonly.value) {
        await newModule();
      }

      // 绑定模块数据库配置
      if (!isBindSuccessfully.value) {
        await bindModulesDeployInfo();
      }

      // 绑定参数配置
      await Promise.all([
        mysqlTableRef.value.bindConfigParameters(),
        spiderTableRef.value.bindConfigParameters(),
      ]);

      Message({
        message: isNewModule.value ? t('创建DB模块并绑定数据库配置成功') : t('绑定配置成功'),
        theme: 'success',
      });
      window.changeConfirm = false;
    } catch (e) {
      console.log(e);
    }

    isSubmintting.value = false;
  };

  function handleReset() {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        const resetData = isNewModule.value ? getFormData() : { version: '', character_set: '' };
        _.merge(formdata, resetData);
        mysqlTableRef.value.handleReset();
        spiderTableRef.value.handleReset();
        nextTick(() => {
          formRef.value.clearValidate();
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins";

  .create-module-loading {
    height: 100%;
  }

  .create-module {
    height: 100%;
    padding-bottom: 28px;

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
