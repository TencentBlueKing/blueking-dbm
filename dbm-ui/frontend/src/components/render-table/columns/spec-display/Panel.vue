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
    height="0"
    placement="bottom"
    :popover-delay="[100, 200]"
    theme="light"
    width="514">
    <slot />
    <template #content>
      <div class="sepc-display-panel">
        <div class="title">{{ data.name }} {{ $t('规格') }}</div>
        <div class="items">
          <div class="item">
            <div class="item__title">CPU：</div>
            <div class="item__content">
              {{
                data.cpu.min === data.cpu.max
                  ? $t('n核', { n: data.cpu.min })
                  : $t('((n-m))核', { n: data.cpu.min, m: data.cpu.max })
              }}
            </div>
          </div>
          <div class="item">
            <div class="item__title">{{ $t('内存') }}：</div>
            <div class="item__content">
              {{ data.mem.min === data.mem.max ? data.mem.min : `(${data.mem.min}~${data.mem.max})` }} G
            </div>
          </div>
          <div
            class="item"
            style="align-items: flex-start">
            <div class="item__title">{{ $t('磁盘') }}：</div>
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
                    {{ data.storage_spec[0].mount_point }}
                  </div>
                  <div class="row_two">
                    {{ data.storage_spec[0].size }}
                  </div>
                  <div class="row_three">
                    {{ data.storage_spec[0].type }}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div
            v-if="!hideQps"
            class="item">
            <div class="item__title">
              {{ $t('单机 QPS') }}
            </div>
            <div class="item__content">
              {{ data.qps.min === data.qps.max ? `${data.qps.min}/s` : `${data.qps.min}/s~${data.qps.max}/s` }}
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
    cpu: {
      max: number;
      min: number;
    };
    id: number;
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[];
    count?: number;
  }

  interface Props {
    data?: SpecInfo;
    hideQps?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    data: () => ({
      id: 1,
      name: '默认规格',
      cpu: {
        min: 0,
        max: 1,
      },
      mem: {
        min: 0,
        max: 1,
      },
      qps: {
        min: 0,
        max: 1,
      },
      count: 1,
      storage_spec: [
        {
          mount_point: '/data',
          size: 0,
          type: '默认',
        },
      ],
    }),
    hideQps: false,
  });
</script>
<style lang="less" scoped>
  .sepc-display-panel {
    display: flex;
    width: 514px;
    padding: 16px 24px 20px 16px;
    margin-top: -12px;
    margin-left: -12px;
    background: #fff;
    border: 1px solid #dcdee5;
    box-shadow: 0 3px 6px 0 #00000029;
    box-sizing: border-box;
    flex-direction: column;

    .title {
      height: 20px;
      margin-bottom: 18px;
      font-size: 12px;
      font-weight: 700;
      line-height: 20px;
      color: #63656e;
    }

    .items {
      display: flex;
      flex-direction: column;
      gap: 18px;

      .item {
        display: flex;
        width: 100%;
        align-items: center;

        &__title {
          min-width: 36px;
          font-size: 12px;
          letter-spacing: 0;
          color: #63656e;
          text-align: right;
        }

        &__content {
          font-size: 12px;
          letter-spacing: 0;
          color: #313238;

          .table {
            display: flex;
            flex-direction: column;

            .cell_common {
              width: 200px;
              height: 42px;
              padding: 11px 16px;
              border: 1px solid #dcdee5;
            }

            .head {
              display: flex;
              width: 100%;
              background: #f0f1f5;

              &_one {
                .cell_common();

                border-bottom: none;
              }

              &_two {
                .cell_common();

                width: 120px;
                border-right: none;
                border-bottom: none;
                border-left: none;
              }

              &_three {
                .cell_common();

                width: 120px;
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
                border-right: none;
                border-left: none;
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
    
  }
</style>
