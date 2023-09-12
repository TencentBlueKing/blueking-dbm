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
        {{ t('新建规则') }}
        <BkTag theme="info">
          {{ t('平台') }}
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="title-spot item-title">
        {{ t('目标集群容量需求') }}<span class="required" />
      </div>
      <BkInput size="default" />
      <div class="title-spot item-title mt-24">
        {{ t('轮值方式') }}<span class="required" />
      </div>
      <BkRadioGroup
        v-model="rotateType"
        type="card">
        <BkRadioButton :label="t('周期轮值')" />
        <BkRadioButton :label="t('自定义轮值')" />
      </BkRadioGroup>
      <div class="title-spot item-title mt-24">
        {{ t('轮值业务') }}<span class="required" />
      </div>
      <BkRadioGroup
        v-model="bizType"
        class="rotate-biz">
        <div class="biz-box">
          <BkRadio :label="t('全部业务')" />
          <div class="biz-box-control">
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
                  show-select-all>
                  <BkOption
                    v-for="(item, index) in bizList"
                    :key="index"
                    :label="item.label"
                    :value="item.value" />
                </BkSelect>
                <DbIcon
                  v-bk-tooltips="{
                    content: t('删除排除项'),
                    theme: 'dark'
                  }"
                  class="ml-10"
                  style="font-size: 16px;color:#979BA5;"
                  type="delete" />
              </template>
            </div>
          </div>
        </div>
        <div class="biz-box">
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
        </div>
      </BkRadioGroup>
      <CycleRotate />
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

  import { useBeforeClose } from '@hooks';

  import CycleRotate from './CycleRotate.vue';

  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const rotateType = ref('');
  const bizType = ref('');

  const bizList = ref([
    {
      value: 'wz',
      label: '王者荣耀',
    },
    {
      value: 'fc',
      label: 'QQ飞车',
    },
  ]);

  const partialBizs = ref([]);
  const isShowSelectExcludeBizBox = ref(false);

  const handleClickAppendExcludeBizs = () => {
    isShowSelectExcludeBizBox.value = true;
  };

  // 点击确定
  const handleConfirm = () => {
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
