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
    height="220"
    placement="right"
    :popover-delay="0"
    theme="light"
    width="420">
    <slot name="hover" />
    <template #content>
      <div class="spec-column-panel">
        <div class="spec-column-panel-title">{{ data.name }} {{ t('规格') }}</div>
        <div class="spec-column-panel-item">
          <div class="item-title">CPU：</div>
          <div class="item-content">
            {{
              data.cpu.min === data.cpu.max
                ? t('n核', { n: data.cpu.min })
                : t('((n-m))台', { n: data.cpu.min, m: data.cpu.max })
            }}
          </div>
        </div>
        <div class="spec-column-panel-item">
          <div class="item-title">{{ t('内存') }}：</div>
          <div class="item-content">
            {{ data.mem.min === data.mem.max ? data.mem.min : `(${data.mem.min}~${data.mem.max})` }}
            G
          </div>
        </div>
        <div class="spec-column-panel-item">
          <div class="item-title">{{ t('磁盘') }}：</div>
          <div class="item-content">
            <div class="mount-point-table">
              <div class="mount-point-table-head">
                <div class="head-one">
                  {{ t('挂载点') }}
                </div>
                <div class="head-two">
                  {{ t('最小容量(G)') }}
                </div>
                <div class="head-three">
                  {{ t('磁盘类别') }}
                </div>
              </div>
              <div
                v-for="(storageSpecItem, storageSpecIndex) in data.storage_spec"
                :key="storageSpecIndex"
                class="table-row">
                <div class="row-one">
                  {{ storageSpecItem.mount_point }}
                </div>
                <div class="row-two">
                  {{ storageSpecItem.size }}
                </div>
                <div class="row-three">
                  {{ storageSpecItem.type }}
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
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      count: number;
      cpu: {
        max: number;
        min: number;
      };
      id: number;
      mem: {
        max: number;
        min: number;
      };
      name: string;
      storage_spec: {
        mount_point: string;
        size: number;
        type: string;
      }[];
    };
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .spec-column-panel {
    display: flex;
    width: 420px;
    height: 220px;
    padding: 16px;
    margin-top: -14px;
    margin-left: -12px;
    background: #fff;
    border: 1px solid #dcdee5;
    box-shadow: 0 3px 6px 0 #00000029;
    box-sizing: border-box;
    flex-direction: column;

    .spec-column-panel-title {
      height: 20px;
      margin-bottom: 12px;
      font-size: 12px;
      font-weight: 700;
      line-height: 20px;
      color: #63656e;
    }

    .spec-column-panel-item {
      display: flex;
      width: 100%;
      height: 32px;
      align-items: center;

      .item-title {
        height: 20px;
        font-size: 12px;
        letter-spacing: 0;
        color: #63656e;
      }

      .item-content {
        height: 20px;
        font-size: 12px;
        letter-spacing: 0;
        color: #313238;

        .mount-point-table {
          display: flex;
          width: 100%;
          flex-direction: column;

          .cell-common {
            width: 140px;
            height: 42px;
            padding: 11px 16px;
            border: 1px solid #dcdee5;
            border-right: 1px solid #dcdee5;
            border-bottom: 1px solid #dcdee5;
          }

          .mount-point-table-head {
            display: flex;
            width: 100%;
            background: #f0f1f5;

            .head-one {
              .cell-common();

              border-right: none;
              border-bottom: none;
            }

            .head-two {
              .cell-common();

              width: 120px;
              border-right: none;
              border-bottom: none;
            }

            .head-three {
              .cell-common();

              width: 82px;
              border-bottom: none;
            }
          }

          .table-row {
            display: flex;
            width: 100%;
            border-top: none;

            .row-one {
              .cell-common();

              border-right: none;
            }

            .row-two {
              .cell-common();

              width: 120px;
              border-right: none;
            }

            .row-three {
              .cell-common();

              width: 82px;
            }
          }
        }
      }
    }
  }
</style>
