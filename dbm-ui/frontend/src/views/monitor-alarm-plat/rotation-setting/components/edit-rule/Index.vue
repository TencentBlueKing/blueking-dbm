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
        {{ pageTitle }}
        <BkTag theme="info">
          {{ t('平台') }}
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="title-spot item-title">
        {{ t('规则名称') }}<span class="required" />
      </div>
      <BkInput
        v-model="ruleName"
        @blur="checkName" />
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

  import {
    createDutyRule,
    updateDutyRule,
  } from '@services/monitor';

  import { useBeforeClose } from '@hooks';

  import type { RowData } from '../content/Index.vue';

  import CustomRotate from './CustomRotate.vue';
  import CycleRotate from './CycleRotate.vue';

  interface Props {
    dbType: string;
    data?: RowData;
    pageType?: string;
  }

  interface Emits {
    (e: 'success'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    pageType: 'create',
    data: undefined,
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const nameTip = ref('');
  const rotateType = ref('0');
  const bizType = ref(0);
  const ruleName = ref('');
  const customRef = ref();
  const cycleRef = ref();
  const isSetCutomEmpty = ref(false);
  // const partialBizs = ref([]);
  // const isShowSelectExcludeBizBox = ref(false);

  const isCreate = computed(() => props.pageType !== 'edit');
  const pageTitle = computed(() => {
    if (props.pageType === 'create') {
      return t('新建规则');
    } if (props.pageType === 'edit') {
      return t('编辑规则');
    }
    return t('克隆规则');
  });

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

  // const bizList = ref<SelectItem[]>([]);

  watch([() => props.pageType, () => props.data], ([type, data]) => {
    if (type !== 'create' && data) {
      // 编辑或者克隆
      ruleName.value = data.name;
      rotateType.value = data.category === 'handoff' ? '0' : '1';
    }
  });

  const checkName = () => {
    if (!ruleName.value) {
      nameTip.value = t('策略名称不能为空');
      return false;
    }
    if (props.pageType === 'clone' && props.data) {
      // 克隆才需要校验
      if (ruleName.value === props.data.name) {
        nameTip.value = t('策略名称与原策略名称相同');
        return false;
      }
      // const ret = await queryMonitorPolicyList({
      //   bk_biz_id: currentBizId,
      //   db_type: props.dbType,
      //   name: ruleName.value,
      //   limit: 10,
      //   offset: 0,
      // });
      // if (ret.results.length !== 0) {
      //   nameTip.value = t('策略名称重复');
      //   return false;
      // }
    }

    nameTip.value = '';
    return true;
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
    const checkNameStatus = checkName();
    if (!checkNameStatus) {
      return;
    }
    if (rotateType.value === '0') {
      const cycleValues = cycleRef.value.getValue();
      const cycleParams = {
        name: ruleName.value,
        priority: 1,
        db_type: props.dbType,
        category: 'handoff',
        effective_time: cycleValues.effective_time,
        end_time: cycleValues.end_time,
        duty_arranges: cycleValues.duty_arranges,
      };
      console.log('params: ', cycleParams);
      if (isCreate.value) {
        // 新建/克隆
        const r = await createDutyRule(cycleParams);
        if (r.is_enabled) {
          // 成功
          emits('success');
        }
        console.log('create cycle rule: ', r);
      } else {
        // 克隆或者编辑
        if (props.data) {
          cycleParams.effective_time = cycleValues.effective_time;
          cycleParams.end_time = cycleValues.end_time;
          const r = await updateDutyRule(props.data.id, cycleParams);
          if (r) {
            // 成功
            emits('success');
          }
          console.log('update cycle rule: ', r);
        }
      }
    } else {
      // 自定义轮值
      const customValues = customRef.value.getValue();
      const customParams = {
        name: ruleName.value,
        priority: 2,
        db_type: props.dbType,
        category: 'regular',
        effective_time: customValues.effective_time,
        end_time: customValues.end_time,
        duty_arranges: customValues.duty_arranges,
      };
      console.log('params: ', customParams);
      if (isCreate.value) {
        // 新建/克隆
        const r = await createDutyRule(customParams);
        if (r.is_enabled) {
          // 成功
          emits('success');
        }
        console.log('create custom rule: ', r);
      } else {
        // 克隆或者编辑
        if (props.data) {
          const r = await updateDutyRule(props.data.id, customParams);
          if (r) {
            // 成功
            emits('success');
          }
          console.log('update custom rule: ', r);
        }
      }
    }
    isShow.value = false;
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    isShow.value = false;
  }

</script>

<style lang="less" scoped>
.main-box {
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
