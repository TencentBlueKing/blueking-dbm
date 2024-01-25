<template>
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="createModuleFormRef"
      class="create-module db-scroll-y"
      :label-width="180"
      :model="formData">
      <DbCard
        class="mb-16"
        :title="t('模块信息')">
        <BkFormItem
          :label="t('模块名称')"
          property="module_name"
          required
          :rules="rules.module_name">
          <BkInput
            v-model="formData.module_name"
            :placeholder="t('由英文字母_数字_连字符_组成')" />
          <span class="belong-business ml-16">{{ t('所属业务') }} : {{ bizInfo.name }}</span>
        </BkFormItem>
      </DbCard>
      <DbCard
        class="mb-16"
        :title="t('绑定数据库配置')">
        <BkFormItem
          :label="t('数据库版本')"
          property="version"
          required>
          <DeployVersion
            v-model="formData.version"
<<<<<<< HEAD
            db-type="mysql"
            :placeholder="t('请选择数据库版本')"
            query-key="mysql" />
=======
            db-type="sqlserver"
            :placeholder="t('请选择数据库版本')"
            query-key="sqlserver" />
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
        </BkFormItem>
        <BkFormItem
          :label="t('字符集')"
          property="character_set"
          required>
          <BkSelect
            v-model="formData.character_set"
            :clearable="false"
            filterable
            :placeholder="t('请选择字符集')">
            <BkOption
              v-for="(item, index) in characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
<<<<<<< HEAD
=======
      </DbCard>
      <DbCard :title="t('参数配置')">
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
        <BkFormItem
          :label="t('数据库配置')"
          property="version"
          required>
          <BkSelect
            v-model="formData.version"
            :clearable="false"
            disabled
            :placeholder="t('请选择数据库版本')">
            <BkOption
              v-for="(item, index) in characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="t('操作系统版本')"
          property="operatingSystemVersion"
          required>
          <BkSelect
            v-model="formData.operatingSystemVersion"
            :clearable="false"
            filterable
            :placeholder="t('请选择操作系统版本')">
            <BkOption
              v-for="item in operatingSystemVersionList"
              :key="item.value"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="t('实例内存分配比率 (50~80%)')"
          property="memoryAllocationRatio"
          required>
          <div class="input-box">
            <BkInput
              v-model="formData.memoryAllocationRatio"
              class="item-input num-input"
              :max="80"
              :min="50"
              :placeholder="t('请输入')"
              type="number" />
            <div class="uint">
              %
            </div>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('最大系统保留内存')"
          property="maxSystemReservedMemory"
          required>
          <div class="input-box">
            <BkInput
              v-model="formData.maxSystemReservedMemory"
              class="item-input num-input"
              :min="1"
              :placeholder="t('请输入')"
              type="number" />
            <div class="uint">
              GB
            </div>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('主从方式')"
          property="haMode"
          required>
          <BkRadioGroup v-model="formData.haMode">
            <BkRadio
              v-for="item in haModeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </DbCard>
<<<<<<< HEAD
      <!-- <DbCard :title="t('参数配置')">
        <BkLoading :loading="configState.loading">
          <ParameterTable
            ref="parameterTableRef"
            :data="configState.data.conf_items"
            :is-anomalies="configState.isAnomalies"
            level="module"
            :origin-data="configState.originConfItems"
            :parameters="configState.parameters" />
        </BkLoading>
      </DbCard> -->
=======
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
    </DbForm>
    <template #action>
      <BkButton
        class="w-88 mt-8"
<<<<<<< HEAD
        :loading="isLoading"
=======
        :loading="submit"
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8 mt-8"
<<<<<<< HEAD
        :disabled="isLoading"
=======
        :disabled="submit"
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
        @click="resetFormData()">
        {{ t('重置') }}
      </BkButton>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { merge } from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createModules } from '@services/source/cmdb';
<<<<<<< HEAD
  import {  saveModulesDeployInfo } from '@services/source/configs';
=======
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import DeployVersion from '@components/apply-items/DeployVersion.vue';

  import { messageSuccess } from '@utils/message';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
<<<<<<< HEAD

  const {
    bizs,
    currentBizId,
  } = useGlobalBizs();
=======
  const globalBizsStore = useGlobalBizs();
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e

  const haModeList = [
    {
      value: 'image',
<<<<<<< HEAD
      label: t('镜像'),
=======
      label: '镜像',
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
    },
    {
      value: 'alwaysOn',
      label: 'always on',
    },
  ];

<<<<<<< HEAD
  const characterSets = ['Chinese_PRC_CI_AS', 'Latin1_General_100_CI_AS'];

  const operatingSystemVersionList = [
    {
      label: t('不限制'),
=======
  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1'];

  const operatingSystemVersionList = [
    {
      label: '不限制',
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
      value: 'noLim',
    },
    {
      label: 'Win 2017',
      value: 'win2017',
    },
    {
      label: 'Win 2018',
      value: 'win2018',
    },
    {
      label: 'Win 2019',
      value: 'win2019',
    },
    {
      label: 'Win 2020',
      value: 'win2020',
    },
  ];

<<<<<<< HEAD
  const bizInfo = bizs.find(info => info.bk_biz_id === currentBizId) || { name: '' };
=======
  const moduleId = Number(route.params.db_module_id);// 模块信息

  const bizInfo = globalBizsStore.bizs.find(info => info.bk_biz_id ===  globalBizsStore.currentBizId) || { name: '' };
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e

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
  const getFormData = () => ({
    module_name: '',
    sqlserver_type: route.params.type,
    version: '',
    camelCase: '', // 数据库配置
    character_set: '', // 字符集
    memoryAllocationRatio: '', // 内存分配比
    maxSystemReservedMemory: '', // 最大系统保留内存
    operatingSystemVersion: '', // 操作系统版本
    haMode: '', // 主从方式
  });

  const createModuleFormRef = ref();
<<<<<<< HEAD
=======
  const submit = ref(false);
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e

  const formData = reactive(getFormData());

  const {
<<<<<<< HEAD
    loading: isLoading,
=======
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
    run: runCreateModules,
  } = useRequest(createModules, {
    manual: true,
    onSuccess(res) {
<<<<<<< HEAD
      if (res.db_module_id) {
=======
      if (res.code === 0) {
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
        messageSuccess(t('创建DB模块并绑定数据库配置成功'));
        window.changeConfirm = false;
        router.go(-1);
      }
    },
  });

<<<<<<< HEAD
  const {
    run: runSaveModuleDeploy,
  } = useRequest(saveModulesDeployInfo, {
    manual: true,
  });

=======
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  /**
   * 提交表单
   */
  const handleSubmit = async () => {
<<<<<<< HEAD
    const clusterType = String(route.query.cluster_type);
    const bizId = Number(route.params.bk_biz_id);
    // 校验表单信息
    await createModuleFormRef.value.validate();
    // 创建模块-接口需替换
    runCreateModules({
      db_module_name: formData.module_name,
      cluster_type: clusterType,
      id: bizId,
    });
    const params = {
      level_name: 'module',
      version: 'deploy_info',
      conf_type: 'deploy',
      bk_biz_id: bizId,
      level_value: Number(route.query.db_module_id),
      meta_cluster_type: clusterType,
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
    // 绑定数据库配置
    runSaveModuleDeploy(params);
=======
    submit.value = true;
    // 校验表单信息
    await createModuleFormRef.value.validate();
    // 新建模块-接口需替换
    runCreateModules(Object.assign(formData, { id: moduleId }));
    submit.value = false;
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
  };

  /**
   * 重置表单
   */
  const  resetFormData = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        merge(formData,  getFormData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.push({
          name: 'serviceApply',
        });
        return;
      }
      router.push({
        name: String(route.query.from),
      });
    },
  });
</script>

<style lang="less" scoped>
  @import "@styles/mixins";

  .create-module{
    .bk-form-content .bk-input,

    .bk-select  {
      width:  435px
    }

    .input-box {
      display: flex;
      width: 100%;
      align-items: center;

      .num-input {
        height: 32px;
      }

      .uint {
        margin-left: 12px;
        font-size: 12px;
        color: #63656E;
      }
    }
  }

</style>
