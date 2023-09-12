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
  <div class="targets-box">
    <div class="left-box">
      <div class="item-box">
        <div class="item">
          <span class="top-bar" />
          AND
          <span class="bottom-bar" />
        </div>
      </div>
    </div>
    <div class="right-box">
      <div class="item-box">
        <div class="item">
          <span class="left-bar" />
          业务
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">

</script>
<style lang="less" scoped>
.targets-box {
  display: flex;
  width: 100%;

  .left-box {
    width: 60px;

    .item-box {
      height: 34px;

      .item {
        position: relative;
        width: 44px;
        height: 22px;
        font-size: 12px;
        line-height: 22px;
        color: #3A84FF;
        text-align: center;
        background: #EDF4FF;
        border-radius: 2px;
        margin-top: 20px;

        .top-bar {
          position: absolute;
          top: -16px;
          left: 20px;
          width: 2px;
          height: 15px;
          background-color: red;
        }

        .bottom-bar {
          position: absolute;
          bottom: -16px;
          left: 20px;
          width: 2px;
          height: 15px;
          background-color: red;
        }
      }
    }
  }

  .right-box {
    flex: 1;

    .item-box {
      width: 100%;

      .item {
        width: 100%;
        background: #FAFBFD;
        border: 1px solid #DCDEE5;
        border-radius: 2px;
        height: 32px;
        position: relative;
        margin-top: -13px;

        .left-bar {
          position: absolute;
          top: 16px;
          left: -40px;
          width: 40px;
          height: 2px;
          background-color: red;
        }
      }
    }
  }
}
</style>
