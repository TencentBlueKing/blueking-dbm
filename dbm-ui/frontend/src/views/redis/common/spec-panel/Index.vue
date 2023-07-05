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
  <BkPopover
    height="222"
    placement="bottom-start"
    theme="light"
    trigger="click"
    width="514">
    <slot name="click" />
    <template #content>
      <div class="panel">
        <div class="title">
          {{ data.name }} {{ $t('规格名称') }}
        </div>
        <div class="item">
          <div class="item__title">
            CPU：
          </div>
          <div class="item__content">
            {{ $t('n核', { n: data.cpu }) }}
          </div>
        </div>
        <div class="item">
          <div class="item__title">
            {{ $t('内存') }}：
          </div>
          <div class="item__content">
            {{ data.mem }} G
          </div>
        </div>
        <div class="item">
          <div class="item__title">
            {{ $t('磁盘') }}：
          </div>
          <div class="item__content">
            <div class="table">
              <div class="head">
                <div class="head_one">
                  {{ $t('挂载点') }}
                </div>
                <div class="head_two">
                  {{ $t('最小容量(G)') }}
                </div>
                <div class="head_three">
                  {{ $t('磁盘类别') }}
                </div>
              </div>
              <div class="row">
                <div class="row_one">
                  {{ data.storage_spec.mount_point }}
                </div>
                <div class="row_two">
                  {{ data.storage_spec.size }}
                </div>
                <div class="row_three">
                  {{ data.storage_spec.type }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  export interface SpecInfo {
    name: string;
    cpu: number;
    id: number;
    mem: number;
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }
    mode?: 'normal' | 'small';
    count?: number;
  }

  interface Props {
    data?: SpecInfo
  }

  withDefaults(defineProps<Props>(), {
    data: () => ({
      mode: 'normal',
      id: 1,
      name: '默认规格',
      cpu: 1,
      mem: 1,
      count: 1,
      storage_spec: {
        mount_point: '/data',
        size: 0,
        type: '默认',
      },
    }),

  });
</script>
<style lang="less" scoped>

.panel {
  display: flex;
  width: 514px;
  height: 222px;
  padding: 16px;
  margin-top: -7px;
  margin-left: -14px;
  background: #FFF;
  border: 1px solid #DCDEE5;
  box-shadow: 0 3px 6px 0 #00000029;
  box-sizing: border-box;
  flex-direction: column;

  .title {
    height: 20px;
    margin-bottom: 12px;
    font-family: MicrosoftYaHei-Bold;
    font-size: 12px;
    font-weight: 700;
    line-height: 20px;
    color: #63656E;
  }

  .item {
    display: flex;
    width: 100%;
    height: 32px;
    align-items: center;

    &__title {
      height: 20px;
      font-family: MicrosoftYaHei;
      font-size: 12px;
      letter-spacing: 0;
      color: #63656E;
    }

    &__content {
      height: 20px;
      font-family: MicrosoftYaHei;
      font-size: 12px;
      letter-spacing: 0;
      color: #313238;

      .table {
        display: flex;
        width: 440px;
        flex-direction: column;

        .cell_common {
          width: 200px;
          height: 42px;
          padding: 11px 16px;
          border: 1px solid #DCDEE5;
          border-right: 1px solid #DCDEE5;
          border-bottom: 1px solid #DCDEE5;
        }

        .head {
          display: flex;
          width: 100%;
          background: #F0F1F5;
          border: 1px solid #DCDEE5;

          &_one {
            .cell_common();

            border-bottom: none;
          }

          &_two {
            .cell_common();

            width: 120px;
            border-bottom: none;
          }

          &_three {
            .cell_common();

            width: 120px;
            border-right: none;
            border-bottom: none;
          }
        }

        .row {
          display: flex;
          width: 100%;

          &_one {
            .cell_common();

          }

          &_two {
            .cell_common();

            width: 120px;
          }

          &_three {
            .cell_common();

            width: 120px;
          }
        }
      }
    }
  }
}
</style>
