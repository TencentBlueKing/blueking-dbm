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
  <BkSideslider
    :before-close="handleClose"
    :is-show="isShow"
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ titleMap[pageType] }}
        <BkTag theme="info">
          {{ t('平台') }}
        </BkTag>
      </span>
    </template>
    <div class="rotation-edit-rule">
      <BkForm
        ref="formRef"
        form-type="vertical"
        :model="formModel"
        :rules="formRules">
        <BkFormItem
          :label="t('规则名称')"
          property="ruleName"
          required>
          <BkInput
            v-model="formModel.ruleName" />
        </BkFormItem>
      </BkForm>
      <div class="name-tip">
        {{ nameTip }}
      </div>
      <div class="title-spot item-title">
        {{ t('轮值方式') }}<span class="required" />
      </div>
      <BkRadioGroup
        v-model="rotateType"
        type="card"
        @change="handleChangeRotateType">
        <BkRadioButton
          v-for="(item, index) in rotateTypeList"
          :key="index"
          :label="item.value">
          {{ item.label }}
        </BkRadioButton>
      </BkRadioGroup>
      <div class="title-spot item-title mt-24">
        {{ t('轮值业务') }}<span class="required" />
      </div>
      <BkRadioGroup
        v-model="bizType"
        class="rotate-biz">
        <div class="biz-box">
          <BkRadio
            :label="0">
            {{ t('全部业务') }}
          </BkRadio>
          <!-- <div class="biz-box-control">
            <div
              class="biz-box-append"
              @click="handleClickAppendExcludeBizs">
              <template v-if="!isShowSelectExcludeBizBox">
                <DbIcon
                  class="mr-6"
                  style="color: #3A84FF;"
                  type="add" />
                <span>{{ t('追加排除业务') }}</span>
              </template>
              <template v-else>
                <BkSelect
                  v-model="partialBizs"
                  class="biz-select"
                  multiple
                  :placeholder="t('请选择排除业务')"
                  show-select-all>
                  <BkOption
                    v-for="(item, index) in bizList"
                    :key="index"
                    :label="item.label"
                    :value="item.value" />
                </BkSelect>
                <DbIcon
                  v-if="partialBizs.length > 0"
                  v-bk-tooltips="{
                    content: t('删除排除项'),
                    theme: 'dark'
                  }"
                  class="ml-10"
                  style="font-size: 16px;color:#979BA5;"
                  type="delete"
                  @click="handleDeleteExcludes" />
              </template>
            </div>
          </div> -->
        </div>
        <!-- <div class="biz-box">
          <BkRadio :label="t('部分业务')" />
          <div class="biz-box-control">
            <BkSelect
              v-model="partialBizs"
              class="biz-select"
              multiple
              show-select-all>
              <BkOption
                v-for="(item, index) in bizList"
                :key="index"
                :label="item.label"
                :value="item.value" />
            </BkSelect>
          </div>
        </div> -->
      </BkRadioGroup>
      <CycleRotate
        v-if="rotateType === '0'"
        ref="cycleRef"
        :data="data" />
      <CustomRotate
        v-else
        ref="customRef"
        :data="data"
        :is-set-empty="isSetCutomEmpty" />
    </div>

    <template #footer>
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    createDutyRule,
    updateDutyRule,
  } from '@services/monitor';

  import { useBeforeClose } from '@hooks';

  import { messageSuccess } from '@utils';

  import type { RowData } from '../content/Index.vue';

  import CustomRotate from './CustomRotate.vue';
  import CycleRotate from './CycleRotate.vue';

  interface Props {
    dbType: string;
    data?: RowData;
    pageType?: string;
    existedNames?: string[];
  }

  interface Emits {
    (e: 'success'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    pageType: 'create',
    data: undefined,
    existedNames: () => ([]),
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const nameTip = ref('');
  const rotateType = ref('0');
  const bizType = ref(0);
  const customRef = ref();
  const cycleRef = ref();
  const isSetCutomEmpty = ref(false);
  const formRef = ref();
  const formModel = reactive({
    ruleName: '',
  });

  // const partialBizs = ref([]);
  // const isShowSelectExcludeBizBox = ref(false);

  const isCreate = computed(() => props.pageType !== 'edit');

  const titleMap = {
    create: t('新建规则'),
    edit: t('编辑规则'),
    clone: t('克隆规则'),
  } as Record<string, string>;

  const rotateTypeList = [
    {
      value: '0',
      label: t('周期轮值'),
    },
    {
      value: '1',
      label: t('自定义轮值'),
    },
  ];

  const formRules = {
    ruleName: [
      {
        validator: (value: string) => {
          if (value.length > 128) {
            // 克隆才需要校验
            return false;
          }
          return true;
        },
        message: t('不能超过 128 个字符'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => {
          if (props.pageType === 'clone' && props.data && value === props.data.name) {
            // 克隆才需要校验
            return false;
          }
          return true;
        },
        message: t('策略名称与原策略名称相同'),
        trigger: 'blur',
      },
      // TODO: 以后看情况是否增加接口支持，暂时先用当前页做冲突检测
      {
        validator: async (value: string) => props.existedNames.every(item => item !== value),
        message: t('策略名称重复'),
        trigger: 'blur',
      },
    ],
  };

  const { run: runCreateDutyRule } = useRequest(createDutyRule, {
    manual: true,
    onSuccess: (createResult) => {
      if (createResult) {
        messageSuccess(t('保存成功'));
        emits('success');
      }
    },
  });

  const { run: runUpdateDutyRule } = useRequest(updateDutyRule, {
    manual: true,
    onSuccess: (updateResult) => {
      if (updateResult) {
        // 成功
        messageSuccess(t('保存成功'));
        emits('success');
      }
    },
  });

  // const bizList = ref<SelectItem[]>([]);

  watch(() => [props.pageType, props.data], () => {
    checkPageTypeAndData();
  });

  const checkPageTypeAndData = () => {
    if (props.pageType !== 'create' && props.data) {
      // 编辑或者克隆
      formModel.ruleName = props.data.name;
      rotateType.value = props.data.category === 'handoff' ? '0' : '1';
      return;
    }
    formModel.ruleName = '';
  };

  const handleChangeRotateType = (value: string) => {
    isSetCutomEmpty.value = value === '1';
  };

  // const handleClickAppendExcludeBizs = () => {
  //   isShowSelectExcludeBizBox.value = true;
  // };

  // const handleDeleteExcludes = () => {
  //   partialBizs.value = [];
  // };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();
    if (rotateType.value === '0') {
      const cycleValues = await cycleRef.value.getValue();
      const cycleParams = {
        name: formModel.ruleName,
        priority: 1,
        db_type: props.dbType,
        category: 'handoff',
        effective_time: cycleValues.effective_time,
        end_time: cycleValues.end_time,
        duty_arranges: cycleValues.duty_arranges,
      };
      if (isCreate.value) {
        // 新建/克隆
        runCreateDutyRule(cycleParams);
      } else {
        // 克隆或者编辑
        if (props.data) {
          cycleParams.effective_time = cycleValues.effective_time;
          cycleParams.end_time = cycleValues.end_time;
          runUpdateDutyRule(props.data.id, cycleParams);
        }
      }
    } else {
      // 自定义轮值
      const customValues = customRef.value.getValue();
      const customParams = {
        name: formModel.ruleName,
        priority: 2,
        db_type: props.dbType,
        category: 'regular',
        effective_time: customValues.effective_time,
        end_time: customValues.end_time,
        duty_arranges: customValues.duty_arranges,
      };
      if (isCreate.value) {
        // 新建/克隆
        runCreateDutyRule(customParams);
      } else {
        // 克隆或者编辑
        if (props.data) {
          runUpdateDutyRule(props.data.id, customParams);
        }
      }
    }
    isShow.value = false;
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    checkPageTypeAndData();
    window.changeConfirm = false;
    isShow.value = false;
  }

</script>

<style lang="less" scoped>
.rotation-edit-rule {
  display: flex;
  width: 100%;
  padding: 24px 40px;
  flex-direction: column;

  .item-title {
    margin-bottom: 6px;
    font-weight: normal;
    color: #63656E;
  }


  .name-tip {
    height: 20px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #EA3636;
  }

  .rotate-biz {
    width: 100%;
    flex-direction: column;
    gap: 12px;

    .biz-box {
      display: flex;
      width: 100%;
      height: 54px;
      padding-left: 17px;
      background: #F5F7FA;
      border-radius: 2px;
      align-items: center;

      .biz-box-control {
        display: flex;
        width: 100%;
        margin-left: 36px;
        align-items: center;

        .biz-select {
          width: 710px;
        }

        .biz-box-append {
          display: flex;
          font-size: 12px;
          color: #3A84FF;
          align-items: center;
          cursor: pointer;
        }
      }
    }
  }
}


</style>
