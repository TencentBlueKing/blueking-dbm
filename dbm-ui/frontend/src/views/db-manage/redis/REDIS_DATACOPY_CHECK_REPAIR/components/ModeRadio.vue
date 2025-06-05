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
  <BkRadioGroup v-model="moduleValue">
    <div class="radio-group">
      <BkRadio
        v-for="item in list"
        :key="item.label"
        class="radio-item"
        :label="item.label">
        <div class="radio-item-content">
          <div class="img-box">
            <DbIcon :type="item.icon" />
          </div>
          <div class="title-box">
            <div class="main-title">
              {{ item.title }}
            </div>
            <div>
              {{ item.subTitle }}
            </div>
          </div>
        </div>
      </BkRadio>
    </div>
  </BkRadioGroup>
</template>

<script setup lang="ts">
  interface Props {
    list: {
      icon: string;
      label: string;
      subTitle: string;
      title: string;
    }[];
  }

  defineProps<Props>();

  const moduleValue = defineModel<string>({
    required: true,
  });
</script>

<style lang="less" scoped>
  .radio-group {
    display: flex;
    flex-direction: column;

    .radio-item {
      margin: 0;
      align-items: flex-start;

      :deep(.bk-radio-input) {
        margin-top: 8px;
      }

      .radio-item-content {
        display: flex;
        margin-left: 5px;
        color: #63656e;

        .img-box {
          font-size: 14px;
        }

        .title-box {
          display: flex;
          margin-left: 4px;
          flex-direction: column;

          .main-title {
            margin-bottom: 4px;
            font-weight: 700;
            color: #63656e;
          }
        }
      }
    }
  }
</style>
