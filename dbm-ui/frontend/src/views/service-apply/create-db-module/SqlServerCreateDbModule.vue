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
            :placeholder="t('由英文字母_数字_连字符_组成')"
            :readonly="isReadonly" />
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
            db-type="sqlserver"
            :placeholder="t('请选择数据库版本')"
            query-key="sqlserver" />
        </BkFormItem>
        <BkFormItem
          :label="t('字符集')"
          property="character_set"
          required>
          <BkSelect
            v-model="formData.character_set"
            :clearable="false"
            :disabled="isBindSuccessfully"
            filterable
            :placeholder="t('请选择字符集')">
            <BkOption
              v-for="(item, index) in listState.characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
      </DbCard>
      <DbCard :title="t('参数配置')">
        <BkFormItem
          :label="t('数据库配置')"
          property="character_set"
          required>
          <BkSelect
            v-model="formData.character_set"
            :clearable="false"
            :disabled="isBindSuccessfully"
            filterable
            :placeholder="t('请选择字符集')">
            <BkOption
              v-for="(item, index) in listState.characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="t('操作系统版本')"
          property="character_set"
          required>
          <BkSelect
            v-model="formData.character_set"
            :clearable="false"
            :disabled="isBindSuccessfully"
            filterable
            :placeholder="t('请选择字符集')">
            <BkOption
              v-for="(item, index) in listState.characterSets"
              :key="index"
              :label="item"
              :value="item" />
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
          property="character_set"
          required>
          <BkRadioGroup>
            <BkRadio
              v-for="item in haModeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </DbCard>
    </DbForm>
    <template #action>
      <BkButton
        class="w-88 mt-8"
        :disabled="disabledSubmit"
        :loading="loadingState.submit"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8 mt-8"
        :disabled="loadingState.submit"
        @click="resetFormData()">
        {{ t('取消') }}
      </BkButton>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { createModules } from '@services/source/cmdb';
  import {
    getLevelConfig,
    saveModulesDeployInfo,
    updateBusinessConfig,
  } from '@services/source/configs';

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    mysqlType,
    type MysqlTypeString,
  } from '@common/const';

  import DeployVersion from '@components/apply-items/DeployVersion.vue';

  import {
    type DiffItem,
    useDiff,
  } from '@views/db-configure/hooks/useDiff';

  type ParameterConfigItem = ServiceReturnType<typeof getLevelConfig>['conf_items'][number]

  // 数据库类型信息
  const ticketType = computed(() => route.params.type as MysqlTypeString);
  const ticketInfo = computed(() => mysqlType[ticketType.value]);

  /**
   * 获取表单基础信息
   */
  const getFormData = () => ({
    module_name: (route.query.module_name ?? '') as string,
    sqlserver_type: ticketType.value,
    version: '',
    character_set: '',
    memoryAllocationRatio: '',
    maxSystemReservedMemory: '',
  });

  const { t } = useI18n();

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const haModeList = [
    {
      value: 'image',
      label: '镜像',
    },
    {
      value: 'alwaysOn',
      label: 'always on',
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

  const isBindSuccessfully = ref(false);
  const paramsConfigDataStringify = ref('');
  const moduleId = ref(route.params.db_module_id ? Number(route.params.db_module_id) : '');// 模块信息
  const createModuleFormRef = ref();

  const formData = reactive(getFormData());

  const listState = reactive({
    versions: [] as string[],
    characterSets: ['utf8', 'utf8mb4', 'gbk', 'latin1'],
  });

  const loadingState = reactive({
    versions: false,
    submit: false,
  });

  const configState = reactive({
    loading: false,
    isAnomalies: false,
    data: {
      name: '',
      version: '',
      description: '',
      conf_items: [],
    } as ServiceReturnType<typeof getLevelConfig>,
    parameters: [] as ParameterConfigItem[],
    originConfItems: [] as ParameterConfigItem[],
  });

  const disabledSubmit = computed(() => !isBindSuccessfully.value
    || paramsConfigDataStringify.value === JSON.stringify(configState.data.conf_items));

  // 业务信息
  const bizId = computed(() => Number(route.params.bk_biz_id));
  const bizInfo = computed(() => globalBizsStore.bizs.find(info => info.bk_biz_id ===  bizId.value) || { name: '' });

  const isNewModule = computed(() => !route.params.db_module_id);
  const isReadonly = computed(() => (isNewModule.value ? !!moduleId.value : true));

  const fetchParams = computed(() => ({
    bk_biz_id: bizId.value,
    level_name: isReadonly.value ? 'module' : 'app',
    level_value: isReadonly.value ? moduleId.value as number : bizId.value as number,
    meta_cluster_type: ticketInfo.value.type,
    conf_type: 'dbconf',
    version: formData.version,
  }));

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  /**
   * 提交表单
   */
  const handleSubmit = async () => {
    loadingState.submit = true;
    try {
      // 校验表单信息
      if (createModuleFormRef.value) {
        await createModuleFormRef.value.validate();
      }

      // 新建模块或已经新建成功则不执行创建
      if (!isReadonly.value) {
        const createResult = await createModules({
          id: bizId.value,
          db_module_name: formData.module_name,
          cluster_type: ticketInfo.value.type,
        });
        moduleId.value = createResult.db_module_id;
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
      console.log(e, 'error');
    }
    loadingState.submit = false;
  };

  /**
   * 绑定数据库配置
   */
  const  bindModulesDeployInfo = () => {
    const params = {
      level_name: 'module',
      version: 'deploy_info',
      conf_type: 'deploy',
      bk_biz_id: bizId.value,
      level_value: moduleId.value as number,
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
  };

  const  resetFormData = () => {
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
  };

  /**
   * 绑定参数配置
   */
  const bindConfigParameters = () => {
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
  };

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        return   router.push({
          name: 'serviceApply',
        });
      }
      router.push({
        name: route.query.from as string,
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
