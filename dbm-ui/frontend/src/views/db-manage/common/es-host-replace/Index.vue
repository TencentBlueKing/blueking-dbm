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
  <div class="es-cluster-replace-render-host-list">
    <table class="node-table">
      <thead>
        <tr>
          <th>
            <span>{{ t('被替换的节点 IP') }}</span>
            <I18nT
              keypath="(共n台_磁盘容量nG)"
              tag="span">
              <span style="padding: 0 4px">
                {{ oldHostList.length }}
              </span>
              <span style="padding: 0 4px">
                {{ nodeDiskTotal }}
              </span>
            </I18nT>
          </th>
          <th>
            <div class="value-result-head-column">
              <div>
                <span>
                  <span>{{ t('新节点 IP') }}</span>
                  <span>(</span>
                  <template v-if="ipSource === 'manual_input' && (isValidated || hostList.length > 0)">
                    <I18nT
                      v-if="oldHostList.length > hostList.length"
                      keypath="已选n台_少n台_共nG"
                      style="color: #ea3636"
                      tag="span">
                      <span>{{ hostList.length }}</span>
                      <span>{{ Math.abs(oldHostList.length - hostList.length) }}</span>
                      <span>{{ localHostDisk }}</span>
                    </I18nT>
                    <I18nT
                      v-else-if="oldHostList.length < hostList.length"
                      keypath="已选n台_多n台_共nG"
                      style="color: #ea3636"
                      tag="span">
                      <span>{{ hostList.length }}</span>
                      <span>{{ Math.abs(oldHostList.length - hostList.length) }}</span>
                      <span>{{ localHostDisk }}</span>
                    </I18nT>
                    <I18nT
                      v-else
                      keypath="已选n台_共nG">
                      <span>{{ hostList.length }}</span>
                      <span>{{ localHostDisk }}</span>
                    </I18nT>
                  </template>
                  <span v-else>
                    {{ t('需n台', { n: oldHostList.length }) }}
                  </span>
                  <span>)</span>
                </span>
                <span
                  :id="hostEditBtnPlaceholderId"
                  class="ml-8" />
              </div>
              <div
                v-if="ipSource === 'manual_input' && hostList.length > 0"
                class="instance-number">
                {{ t('实例数量') }}
              </div>
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <div class="original-ip-box">
              <div
                v-for="nodeItem in oldHostList"
                :key="nodeItem.bk_host_id"
                class="ip-tag">
                <span>{{ nodeItem.ip }}</span>
                <DbIcon
                  class="remove-btn"
                  type="close"
                  @click="handleRemoveNode(nodeItem)" />
              </div>
            </div>
          </td>
          <td>
            <ResourceHostSelect
              v-if="ipSource === 'manual_input'"
              v-model="hostList"
              :data="data"
              :disable-host-method="disableHostMethod"
              :placehoder-id="hostEditBtnPlaceholderId"
              @update:model-value="handleValueChange" />
            <ResourcePoolSelector
              v-else
              v-model="resourceSpec"
              :cloud-info="cloudInfo"
              :data="data"
              :error="ipSource !== 'manual_input' && isValidated && resourceSpec.spec_id < 1"
              @update:model-value="handleValueChange" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="tsx">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostInfo } from '@services/types';

  import { random } from '@utils';

  import ResourceHostSelect from './components/ResourceHostSelect.vue';
  import ResourcePoolSelector from './components/ResourcePoolSelector.vue';

  export interface TReplaceNode {
    // 集群id
    clusterId: number;
    hostList: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_disk: number;
      bk_host_id: number;
      instance_num?: number;
      ip: string;
    }[];
    oldHostList: {
      bk_cloud_id: number;
      bk_cloud_name: string;
      bk_host_id: number;
      host_info: HostInfo;
      ip: string;
      related_instances: {
        bk_instance_id: number;
      }[];
    }[];
    // 扩容资源池
    resourceSpec: {
      count: number;
      instance_num: number;
      spec_id: number;
    };
    // 集群的节点类型
    role: string;
    // 资源池规格集群类型
    specClusterType: string;
    // 资源池规格集群类型
    specMachineType: string;
  }

  interface Ivalue {
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  interface Props {
    cloudInfo: {
      id: number;
      name: string;
    };
    data: TReplaceNode;
    disableHostMethod?: (params: TReplaceNode['hostList'][0]) => string | boolean;
    ipSource: string;
  }

  type Emits = (e: 'removeNode', node: TReplaceNode['oldHostList'][number]) => void;

  interface Exposes {
    getValue: () => Promise<{
      new_nodes: Ivalue[];
      old_nodes: Ivalue[];
      resource_spec: TReplaceNode['resourceSpec'];
    }>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const oldHostList = defineModel<TReplaceNode['oldHostList']>('oldHostList', {
    required: true,
  });
  const hostList = defineModel<TReplaceNode['hostList']>('hostList', {
    required: true,
  });
  const resourceSpec = defineModel<TReplaceNode['resourceSpec']>('resourceSpec', {
    required: true,
  });

  const { t } = useI18n();

  const hostEditBtnPlaceholderId = `replaceHostEditBtn${random()}`;
  const isValidated = ref(false);

  const nodeDiskTotal = computed(() =>
    oldHostList.value.reduce((result, item) => result + (item.host_info?.bk_disk || 0), 0),
  );
  const localHostDisk = computed(() => hostList.value.reduce((result, item) => result + ~~Number(item.bk_disk), 0));

  const isError = computed(() => {
    if (oldHostList.value.length < 1) {
      return false;
    }
    if (props.ipSource === 'manual_input') {
      return hostList.value.length > 0 && hostList.value.length !== oldHostList.value.length;
    }

    return resourceSpec.value.spec_id < 1;
  });

  watch(
    () => props.ipSource,
    () => {
      isValidated.value = false;
    },
  );

  // 移除节点
  const handleRemoveNode = (node: TReplaceNode['oldHostList'][0]) => {
    oldHostList.value = oldHostList.value.reduce(
      (result, item) => {
        if (item.bk_host_id !== node.bk_host_id) {
          result.push(item);
        }
        return result;
      },
      [] as TReplaceNode['oldHostList'],
    );
    window.changeConfirm = true;
    emits('removeNode', node);
  };

  // 资源池自动匹配不需要校验主机数
  const handleValueChange = () => {
    isValidated.value = false;
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue() {
      isValidated.value = true;
      if (isError.value) {
        return Promise.reject();
      }

      if (oldHostList.value.length < 1) {
        return Promise.resolve({
          new_nodes: [],
          old_nodes: [],
          resource_spec: {
            count: 0,
            instance_num: 0,
            spec_id: 0,
          },
        });
      }
      return Promise.resolve({
        new_nodes: hostList.value.map((hostItem) => ({
          bk_biz_id: hostItem.bk_biz_id,
          bk_cloud_id: hostItem.bk_cloud_id,
          bk_host_id: hostItem.bk_host_id,
          instance_num: hostItem.instance_num,
          ip: hostItem.ip,
        })),
        old_nodes: oldHostList.value.map((nodeItem) => ({
          bk_cloud_id: nodeItem.bk_cloud_id,
          bk_host_id: nodeItem.bk_host_id,
          ip: nodeItem.ip,
        })),
        resource_spec: {
          ...resourceSpec.value,
          count: oldHostList.value.length,
        },
      });
    },
  });
</script>
<style lang="less">
  .es-cluster-replace-render-host-list {
    position: relative;
    border-bottom: 1px solid #dcdee5;

    .node-table {
      width: 100%;
      font-size: 12px;
      table-layout: fixed;

      th,
      td {
        width: 50%;
        height: 42px;
        font-weight: normal;
        text-align: left;
        border: none;
      }

      th {
        padding: 0 16px;
        color: #313238;
        background: #f0f1f5;

        &:nth-child(2) {
          background: #eaebf0;
        }
      }

      td {
        background: #fff;

        &:nth-child(2) {
          background: #fcfcfc;
        }
      }

      .value-result-head-column {
        display: flex;

        .instance-number {
          padding-right: 34px;
          margin-left: auto;
          text-align: right;
        }
      }

      .original-ip-box {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100%;

        .ip-tag {
          display: inline-flex;
          width: 130px;
          height: 22px;
          padding: 0 6px;
          margin: 2px 4px;
          background: #f0f1f5;
          border-radius: 2px;
          align-items: center;
          justify-content: center;

          & ~ .ip-tag {
            margin-top: 12px;
          }
        }

        .remove-btn {
          margin-left: auto;
          font-size: 14px;
          cursor: pointer;

          &:hover {
            color: #3a84ff;
          }
        }
      }

      .ip-edit-btn {
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }
    }
  }
</style>
