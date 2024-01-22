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
            filterable
            :placeholder="t('请选择字符集')">
            <BkOption
              v-for="(item, index) in characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
      </DbCard>
      <DbCard :title="t('参数配置')">
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
    </DbForm>
    <template #action>
      <BkButton
        class="w-88 mt-8"
        :loading="submit"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8 mt-8"
        :disabled="submit"
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

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import DeployVersion from '@components/apply-items/DeployVersion.vue';

  import { messageSuccess } from '@utils/message';

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

  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1'];

  const operatingSystemVersionList = [
    {
      label: '不限制',
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

  const moduleId = Number(route.params.db_module_id);// 模块信息

  const bizInfo = globalBizsStore.bizs.find(info => info.bk_biz_id ===  globalBizsStore.currentBizId) || { name: '' };

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
  const submit = ref(false);

  const formData = reactive(getFormData());

  const {
    run: runCreateModules,
  } = useRequest(createModules, {
    manual: true,
    onSuccess(res) {
      if (res.code === 0) {
        messageSuccess(t('创建DB模块并绑定数据库配置成功'));
        window.changeConfirm = false;
        router.go(-1);
      }
    },
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  /**
   * 提交表单
   */
  const handleSubmit = async () => {
    submit.value = true;
    // 校验表单信息
    await createModuleFormRef.value.validate();
    // 新建模块-接口需替换
    runCreateModules(Object.assign(formData, { id: moduleId }));
    submit.value = false;
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
