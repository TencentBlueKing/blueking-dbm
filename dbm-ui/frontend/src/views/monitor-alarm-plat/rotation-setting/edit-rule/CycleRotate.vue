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
  <div class="title-spot item-title mt-24">
    {{ t('轮值人员') }}<span class="required" />
    <span class="title-tip">（{{ t('排班时将会按照人员的顺序进行排班，可拖动 Tag 进行排序') }}）</span>
  </div>
  <div class="duty-box mt-24">
    <div class="duty-item">
      <div class="title-spot item-title">
        {{ t('单次值班人数') }}<span class="required" />
      </div>
      <BkInput
        class="input-item"
        type="number">
        <template #suffix>
          <span class="suffix-slot">人</span>
        </template>
      </BkInput>
    </div>
    <div class="duty-item">
      <div class="title-spot item-title">
        {{ t('单班轮值天数') }}<span class="required" />
      </div>
      <BkInput
        class="input-item"
        type="number">
        <template #suffix>
          <span class="suffix-slot">{{ t('天') }}</span>
        </template>
      </BkInput>
    </div>
  </div>
  <div class="title-spot item-title mt-24">
    {{ t('轮值起止时间') }}<span class="required" />
  </div>
  <BkDatePicker
    ref="datePickerRef"
    append-to-body
    clearable
    :model-value="dateTimeRange"
    style="width:100%;"
    type="datetimerange"
    @change="handlerChangeDatetime"
    @pick-success="handleConfirmDatetime" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  const { t } = useI18n();

  const dateTimeRange = ref<[Date, Date]>([new Date(Date.now() - 24 * 60 * 60 * 1000), new Date()]);

  const handlerChangeDatetime = (range: [Date, Date]) => {
    dateTimeRange.value = range;
  };

  const handleConfirmDatetime = () => {
    console.log('select: ', dateTimeRange.value);
  };

</script>
<style lang="less" scoped>
.item-title {
  margin-bottom: 6px;
  font-weight: normal;
  color: #63656E;

  .title-tip {
    margin-left: 6px;
    font-size: 12px;
    color: #979BA5;
  }
}

.duty-box {
  display: flex;
  width: 100%;
  justify-content: space-between;

  .duty-item {
    display: flex;
    width: 420px;
    flex-direction: column;
    gap: 6px;

    .input-item {
      height: 32px;

      :deep(.bk-input--number-control) {
        display: none;
      }
    }

    :deep(.suffix-slot) {
      width: 30px;
      height: 30px;
      line-height: 30px;
      text-align: center;
      background: #FAFBFD;
      border-left: 1px solid #C4C6CC;
    }
  }
}
</style>
