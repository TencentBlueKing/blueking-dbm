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
  <SmartAction
    class="apply-hdfs-page"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      :label-width="165"
      :model="formData"
      :rules="rules"
      style="margin-bottom: 16px;">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <ClusterName v-model="formData.details.cluster_name" />
        <ClusterAlias v-model="formData.details.cluster_alias" />
        <CloudItem
          v-model="formData.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem
        v-model="formData.details.city_code" /> -->
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('Hadoop版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="formData.details.db_version"
            class="item-input"
            filterable
            :input-search="false"
            :loading="isDbVersionLoading">
            <BkOption
              v-for="item in dbVersionList"
              :key="item"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="$t('服务器选择')"
          property="details.ip_source"
          required>
          <BkRadioGroup
            v-model="formData.details.ip_source">
            <BkRadioButton
              label="resource_pool"
              style="width: 218px;">
              {{ $t('自动从资源池匹配') }}
            </BkRadioButton>
            <BkRadioButton
              label="manual_input"
              style="width: 218px;">
              {{ $t('手动录入IP') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <Transition
          mode="out-in"
          name="dbm-fade">
          <div
            v-if="formData.details.ip_source === 'manual_input'"
            class="mb-24">
            <DbFormItem
              property="details.nodes.namenode">
              <template #label>
                <div style="font-size: 12px; line-height: 16px; text-align: right;">
                  <p>NameNode</p>
                  <p>Zookeepers/JournalNodes</p>
                </div>
              </template>
              <div>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="nodeAndZookerperMergeList"
                  :disable-dialog-submit-method="nameAndZookeeperMergeHostDisableDialogSubmitMethod"
                  :disable-host-method="disableHostMethod"
                  required
                  :show-view="false"
                  style="display: inline-block;"
                  @change="handleNameAndZookeeperMergeHostChange">
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="至少n台_最多n台_已选n台"
                      style="font-size: 14px; color: #63656e;"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56;"> 3 </span>
                      <span style="font-weight: bold; color: #2dcb56;"> 5 </span>
                      <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                    </I18nT>
                  </template>
                  <template #desc>
                    {{ $t('至少3台_最多5台_机器可复用_建议规格至少为2核4G') }}
                  </template>
                </IpSelector>
              </div>
              <HdfsHostTable
                v-model:data="nodeAndZookerperMergeList"
                :biz-id="formData.bk_biz_id"
                @change="handleNameAndZookeeperChange" />
            </DbFormItem>
            <DbFormItem
              label="DataNodes"
              property="details.nodes.datanode"
              required>
              <div>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.datanode"
                  :disable-dialog-submit-method="dataNodeDisableDialogSubmitMethod"
                  :disable-host-method="datanodeDisableHostMethod"
                  required
                  :show-view="false"
                  style="display: inline-block;"
                  @change="handleDatanodeChange">
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="至少n台_已选n台"
                      style="font-size: 14px; color: #63656e;"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56;"> 2 </span>
                      <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                    </I18nT>
                  </template>
                  <template #desc>
                    {{ $t('至少2台_建议规格至少为2核4G') }}
                  </template>
                </IpSelector>
              </div>
              <RenderHostTable
                v-model:data="formData.details.nodes.datanode"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
            <BkFormItem
              :label="$t('访问端口')"
              required>
              <div class="access-port-box item-input">
                <table>
                  <tr class="port-block">
                    <td>{{ $t('http端口') }}</td>
                    <td>
                      <BkFormItem property="details.http_port">
                        <BkInput
                          v-model="formData.details.http_port"
                          clearable
                          :min="1"
                          show-clear-only-hover
                          style="width: 130px;"
                          type="number" />
                        <span class="input-desc">{{ $t('禁用2181_8480_8485') }}</span>
                      </BkFormItem>
                    </td>
                  </tr>
                  <tr class="port-block">
                    <td>{{ $t('rpc端口') }}</td>
                    <td>
                      <BkFormItem property="details.rpc_port">
                        <BkInput
                          v-model="formData.details.rpc_port"
                          clearable
                          :min="1"
                          show-clear-only-hover
                          style="width: 130px;"
                          type="number" />
                        <span class="input-desc">{{ $t('禁用2181_8480_8485') }}</span>
                      </BkFormItem>
                    </td>
                  </tr>
                </table>
              </div>
            </BkFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              label="NameNode"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="$t('规格')"
                  property="details.resource_spec.namenode.spec_id"
                  required>
                  <SpecSelector
                    ref="specNamenodeRef"
                    v-model="formData.details.resource_spec.namenode.spec_id"
                    cluster-type="hdfs"
                    machine-type="hdfs_master" />
                </BkFormItem>
                <BkFormItem
                  :label="$t('数量')"
                  property="details.resource_spec.namenode.count"
                  required>
                  <BkInput
                    v-model="formData.details.resource_spec.namenode.count"
                    disabled
                    type="number" />
                  <span class="input-desc">{{ $t('n台', [2]) }}</span>
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              label="Zookeepers/JournalNodes"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="$t('规格')"
                  property="details.resource_spec.zookeeper.spec_id"
                  required>
                  <SpecSelector
                    ref="specZookeeperRef"
                    v-model="formData.details.resource_spec.zookeeper.spec_id"
                    cluster-type="hdfs"
                    machine-type="hdfs_master" />
                </BkFormItem>
                <BkFormItem
                  :label="$t('数量')"
                  property="details.resource_spec.zookeeper.count"
                  required>
                  <div style="display: flex; align-items: center;">
                    <span style="flex-shrink: 0;">
                      <BkInput
                        v-model="formData.details.resource_spec.zookeeper.count"
                        :max="3"
                        :min="1"
                        type="number" />
                    </span>
                    <span
                      class="input-desc pr-12"
                      style="line-height: 16px;">
                      {{ $t('1_3台_小于3时从Namenode节点复用') }}
                    </span>
                  </div>
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              label="DataNodes"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="$t('规格')"
                  property="details.resource_spec.datanode.spec_id"
                  required>
                  <SpecSelector
                    ref="specDatanodeRef"
                    v-model="formData.details.resource_spec.datanode.spec_id"
                    cluster-type="hdfs"
                    machine-type="hdfs_datanode" />
                </BkFormItem>
                <BkFormItem
                  :label="$t('数量')"
                  property="details.resource_spec.datanode.count"
                  required>
                  <BkInput
                    v-model="formData.details.resource_spec.datanode.count"
                    :min="2"
                    type="number" />
                  <span class="input-desc">
                    {{ $t('至少n台', { n: 2 }) }}
                  </span>
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="$t('总容量')"
              required>
              <BkInput
                disabled
                :model-value="totalCapacity"
                style="width: 184px;" />
              <span class="input-desc">G</span>
            </BkFormItem>
          </div>
        </Transition>
        <BkFormItem
          :label="$t('备注')"
          property="remark">
          <BkInput
            v-model="formData.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px;"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
    <template #action>
      <div>
        <BkButton
          :loading="baseState.isSubmitting"
          style="width: 88px;"
          theme="primary"
          @click="handleSubmit">
          {{ $t('提交') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleReset">
          {{ $t('重置') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ $t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
</template>
<script setup lang="ts">
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types/common';
  import type { HostDetails } from '@services/types/ip';
  import { getVersions } from '@services/versionFiles';

  import {
    useApplyBase,
    useInfo,
  } from '@hooks';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import HdfsHostTable, {
    type IHostTableData,
  } from '@components/cluster-common/big-data-host-table/HdfsHostTable.vue';
  import RenderHostTable from '@components/cluster-common/big-data-host-table/RenderHostTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';
  const { t } = useI18n();

  const genDefaultFormData = () => ({
    bk_biz_id: '' as number | '',
    ticket_type: 'HDFS_APPLY',
    details: {
      bk_cloud_id: '',
      db_app_abbr: '',
      cluster_name: '',
      cluster_alias: '',
      city_code: '',
      db_version: '',
      ip_source: 'resource_pool',
      nodes: {
        namenode: [] as Array<IHostTableData>,
        zookeeper: [] as Array<IHostTableData>,
        datanode: [] as Array<IHostTableData>,
      },
      resource_spec: {
        zookeeper: {
          spec_id: '',
          count: 3,
        },
        datanode: {
          spec_id: '',
          count: 2,
        },
        namenode: {
          spec_id: '',
          count: 2,
        },
      },
      http_port: 50070,
      rpc_port: 9000,
    },
    remark: '',
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const formRef = ref();
  const specDatanodeRef = ref();
  const specNamenodeRef = ref();
  const specZookeeperRef = ref();
  const isDbVersionLoading = ref(true);
  const dbVersionList = shallowRef<Array<string>>([]);
  const formData = reactive(genDefaultFormData());
  const nodeAndZookerperMergeList = shallowRef<Array<IHostTableData>>([]);
  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const totalCapacity = ref(0);

  const rules = {
    'details.nodes.namenode': [
      {
        required: true,
        validator: () => formData.details.nodes.namenode.length === 2
          && formData.details.nodes.zookeeper.length === 3,
        message: t('NameNode必须两台_Zookeepers_JournalNodes必须三台'),
        trigger: 'change',
      },
    ],
    'details.nodes.datanode': [
      {
        validator: (value: Array<any>) => value.length >= 2,
        message: t('DataNodes至少2台'),
        trigger: 'change',
      },
    ],
    'details.http_post': [
      {
        validator: () => formData.details.http_port,
        message: t('访问端口必填'),
        trigger: 'change',
      },
      {
        validator: (value: number) => {
          console.log('hhto post = ', value);
          return ![2181, 8480, 8485].includes(value);
        },
        message: t('禁用2181_8480_8485'),
        trigger: 'change',
      },
    ],
    'details.rpc_port': [
      {
        validator: () => formData.details.rpc_port,
        message: t('访问端口必填'),
        trigger: 'change',
      },
      {
        validator: (value: number) => ![2181, 8480, 8485].includes(value),
        message: t('禁用2181_8480_8485'),
        trigger: 'change',
      },
    ],
  };

  watch(() => formData.details.resource_spec.datanode, () => {
    const count = Number(formData.details.resource_spec.datanode.count);
    if (specDatanodeRef.value) {
      const { storage_spec: storageSpec = [] } = specDatanodeRef.value.getData();
      const disk = storageSpec.reduce((total: number, item: { size: number }) => total + Number(item.size || 0), 0);
      totalCapacity.value = disk * count;
    }
  }, { flush: 'post', deep: true });

  // 获取 DB 版本列表
  getVersions({
    query_key: 'hdfs',
  }).then((data) => {
    dbVersionList.value = data;
  })
    .finally(() => {
      isDbVersionLoading.value = false;
    });

  const {
    baseState,
    bizState,
    handleCreateAppAbbr,
    handleCreateTicket,
    handleCancel,
  } = useApplyBase();

  // 切换业务，需要重置 IP 相关的选择
  function handleChangeBiz(info: BizItem) {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    nodeAndZookerperMergeList.value = [];
    formData.details.nodes.namenode = [];
    formData.details.nodes.zookeeper = [];
    formData.details.nodes.datanode = [];
  }
  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    nodeAndZookerperMergeList.value = [];
    formData.details.nodes.namenode = [];
    formData.details.nodes.zookeeper = [];
    formData.details.nodes.datanode = [];
  }

  // ip 选择器提交按钮校验
  const nameAndZookeeperMergeHostDisableDialogSubmitMethod = (hostList: Array<any>) => {
    if (hostList.length < 3 || hostList.length > 5) {
      return t('至少3台_最多5台');
    }
    return false;
  };

  const handleNameAndZookeeperMergeHostChange = (data: Array<HostDetails>) => {
    nodeAndZookerperMergeList.value = data;
  };

  const handleNameAndZookeeperChange = (nameNode: Array<IHostTableData>, zookeeper: Array<IHostTableData>) => {
    formData.details.nodes.namenode = nameNode;
    formData.details.nodes.zookeeper = zookeeper;
  };
  // ip 选择器提交按钮校验
  const dataNodeDisableDialogSubmitMethod = (hostList: Array<any>) => hostList.length < 2;
  // ip 主机状态校验
  const disableHostMethod = (data: any, list: any[]) => {
    if (list.length >= 5 && !list.find(item => item.host_id === data.host_id)) {
      return t('至少n台_最多n台_已选n台', [3, 5, list.length]);
    }

    return false;
  };
  const datanodeDisableHostMethod = (data: any) => {
    const hostIdMap = nodeAndZookerperMergeList.value.reduce((result, item) => ({
      ...result,
      [item.host_id]: true,
    }), {} as Record<number, boolean>);

    return hostIdMap[data.host_id] ? t('主机已被使用') : false;
  };
  const handleDatanodeChange = (data: Array<HostDetails>) => {
    formData.details.nodes.datanode = data;
  };

  // 提交
  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        baseState.isSubmitting = true;
        const mapIpField = (ipList: Array<IHostTableData>) => ipList.map(item => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          bk_biz_id: item.biz.id,
        }));

        const getDetails = () => {
          const details: Record<string, any> = { ...markRaw(formData.details) };

          if (formData.details.ip_source === 'resource_pool') {
            delete details.nodes;
            return {
              ...details,
              resource_spec: {
                zookeeper: {
                  ...details.resource_spec.zookeeper,
                  ...specZookeeperRef.value.getData(),
                  count: Number(details.resource_spec.zookeeper.count),
                },
                namenode: {
                  ...details.resource_spec.namenode,
                  ...specNamenodeRef.value.getData(),
                  count: Number(details.resource_spec.namenode.count),
                },
                datanode: {
                  ...details.resource_spec.datanode,
                  ...specDatanodeRef.value.getData(),
                  count: Number(details.resource_spec.datanode.count),
                },
              },
            };
          }

          delete details.resource_spec;
          return {
            ...details,
            nodes: {
              zookeeper: mapIpField(formData.details.nodes.zookeeper),
              namenode: mapIpField(formData.details.nodes.namenode),
              datanode: mapIpField(formData.details.nodes.datanode),
            },
          };
        };

        const params = {
          ...formData,
          details: getDetails(),
        };
        // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
        bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
      });
  };

  // 重置表单
  const handleReset = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, genDefaultFormData());
        formRef.value.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };
</script>
<style lang="less">
  .apply-hdfs-page {
    display: block;

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }

    .item-input {
      width: 435px;
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    .resource-pool-item {
      width: 655px;
      padding: 24px 0;
      background-color: #F5F7FA;
      border-radius: 2px;

      .bk-form-item {
        .bk-form-label {
          width: 120px !important;
        }

        .bk-form-content {
          margin-left: 120px !important;

          .bk-select,
          .bk-input {
            width: 314px;
          }
        }
      }
    }

    .access-port-box {
      padding: 16px 10px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;

      .bk-input {
        width: 123px;
      }

      .bk-form-label {
        width: 0 !important;
      }

      table {
        td:nth-child(2) {
          padding: 0 12px 0 8px;
        }

        tr:nth-child(n+2) {
          td {
            padding-top: 24px;
          }
        }
      }
    }
  }
</style>
