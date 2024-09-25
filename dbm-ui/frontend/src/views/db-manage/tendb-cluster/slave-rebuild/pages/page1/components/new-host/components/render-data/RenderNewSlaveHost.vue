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
  <TableEditSelect
    ref="editSelectRef"
    :disabled="!clusterData || (clusterData && localValue === 'resource_pool')"
    :input-search="false"
    :list="optionList"
    :model-value="localValue"
    :placeholder="t('请选择')"
    :select-disabled="!clusterData"
    :select-display-fun="selectDisplayFun"
    @change="(value) => handleChange(value as string)">
    <template #option="{ optionItem }">
      <div class="spec-display">
        {{ optionItem.name }}
        <span class="spec-display-count">{{ countMap[optionItem.id] }}</span>
      </div>
    </template>
  </TableEditSelect>
  <!-- <ResourcePoolManualSelector
    v-model:is-show="isShowResourcePoolSelector"
    :disable-dialog-submit-method="disablePoolDialogSubmitMethod"
    :disable-host-method="disablePoolHostMethod"
    @change="handlePoolHostChange">
    <template #submitTips="{ hostList }">
      <I18nT
        keypath="需n台_已选n台"
        style="font-size: 14px; color: #63656e"
        tag="span">
        <span style="font-weight: bold; color: #2dcb56"> 1 </span>
        <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length || 0 }} </span>
      </I18nT>
    </template>
  </ResourcePoolManualSelector>
  <IpSelector
    v-if="clusterData"
    v-model:show-dialog="isShowIpSelector"
    :biz-id="currentBizId"
    button-text=""
    :cloud-info="{
      id: clusterData.bkCloudId,
      name: clusterData.bkCloudName,
    }"
    :disable-dialog-submit-method="disableIdleDialogSubmitMethod"
    :disable-host-method="disableIdleHostMethod"
    :show-view="false"
    @change="handleIdleHostChange">
    <template #submitTips="{ hostList: resultHostList }">
      <I18nT
        keypath="需n台_已选n台"
        style="font-size: 14px; color: #63656e"
        tag="span">
        <span
          class="number"
          style="color: #2dcb56">
          1
        </span>
        <span
          class="number"
          style="color: #3a84ff">
          {{ resultHostList.length }}
        </span>
      </I18nT>
    </template>
  </IpSelector> -->
</template>

<!-- <script lang="ts">
  const poolHostSelectMemo: { [key: string]: Record<string, boolean> } = {};
  const idleHostSelectMemo: { [key: string]: Record<string, boolean> } = {};
</script> -->

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  // import DbResourceModel from '@services/model/db-resource/DbResource';
  // import { fetchList, getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  // import { checkHost, getHostTopo } from '@services/source/ipchooser'
  // import type { HostInfo } from '@services/types/ip';
  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  // import IpSelector from '@components/ip-selector/IpSelector.vue';
  import TableEditSelect from '@views/db-manage/tendb-cluster/common/edit/SelectInput.vue';

  // import { random } from '@utils';
  // import ResourcePoolManualSelector from '../resource-pool-manual-selector/Index.vue';
  import type { IDataRow } from './Row.vue';

  // import { ipv4 } from '@/common/regex';

  interface Props {
    clusterData?: IDataRow['oldSlave'];
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  // const instanceKey = `render_host_instance_key_${random()}`;
  // poolHostSelectMemo[instanceKey] = {};
  // idleHostSelectMemo[instanceKey] = {};

  const optionList = [
    {
      id: 'resource_pool',
      name: t('资源池自动匹配'),
      tooltips: t('当前为资源池自动匹配，切换类型将会清空并需重新选择'),
    },
    // {
    //   id: 'resource_pool_manual',
    //   name: t('资源池手动选择'),
    //   tooltips: t('当前填写的主机为资源池主机，切换类型将会清空并需重新选择')
    // },
    // {
    //   id: 'manual_input',
    //   name: t('业务空闲机'),
    //   tooltips: t('当前填写的主机为业务空闲机，切换类型将会清空并需重新选择')
    // },
  ];

  // const rules = [
  // {
  //   validator: (value: string) => {
  //     if (['resource_pool_manual', 'manual_input'].includes(value)) {
  //       return false
  //     }
  //     return Boolean(value)
  //   },
  //   message: t('新从库主机不能为空'),
  // },
  // {
  //   validator: (value: string) => {
  //     if (value !== "resource_pool") {
  //       return ipv4.test(value)
  //     }
  //     return true
  //   },
  //   message: t('IP格式错误'),
  // },
  // {
  //   validator: (value: string) => {
  //     const currentSelectItem = editSelectRef.value!.getCurrentItem()
  //     if (currentSelectItem && currentSelectItem.id === "resource_pool_manual") {
  //       return fetchList({
  //         bk_biz_id: currentBizId,
  //         hosts: value,
  //         limit: 10,
  //         offset: 0
  //       }).then(resourceResult => {
  //         if (resourceResult.results.length === 0) {
  //           return false
  //         }
  //         poolHostSelectMemo[instanceKey] = {};
  //         localHostList.value = resourceResult.results.map(hostItem => ({
  //           bk_biz_id: hostItem.bk_biz_id,
  //           bk_cloud_id: hostItem.bk_cloud_id,
  //           bk_host_id: hostItem.bk_host_id,
  //           ip: hostItem.ip
  //         }));
  //         poolHostSelectMemo[instanceKey][value] = true;
  //         return true
  //       })
  //     }
  //     return true
  //   },
  //   message: t('该主机在资源池中不存在'),
  // },
  // {
  //   validator: (value: string) => {
  //     const currentSelectItem = editSelectRef.value!.getCurrentItem()
  //     if (currentSelectItem && currentSelectItem.id === "manual_input") {
  //       return checkHost({
  //         ip_list: [value],
  //         mode: "idle_only",
  //         scope_list: [
  //           {
  //             scope_id: currentBizId,
  //             scope_type: "biz",
  //             bk_cloud_id: props.clusterData?.bkCloudId || 0
  //           }
  //         ]
  //       }).then(hostList => {
  //         if (hostList.length === 0) {
  //           return false
  //         }
  //         idleHostSelectMemo[instanceKey] = {};
  //         localHostList.value = hostList.map(hostItem => ({
  //           bk_biz_id: hostItem.biz.id,
  //           bk_cloud_id: hostItem.cloud_id,
  //           bk_host_id: hostItem.host_id,
  //           ip: hostItem.ip
  //         }));
  //         idleHostSelectMemo[instanceKey][value] = true;
  //         return true
  //       })
  //     }
  //     return true
  //   },
  //   message: t('该业务空闲机中不存在'),
  // },
  // {
  //   validator: (value: string) => {
  //     const otherAllSelectHostMap = getOtherAllSelectHostMap(poolHostSelectMemo)
  //     if (otherAllSelectHostMap[value]) {
  //       return false;
  //     }
  //     return true;
  //   },
  //   message: t('资源池IP重复'),
  // },
  // {
  //   validator: (value: string) => {
  //     const otherAllSelectHostMap = getOtherAllSelectHostMap(idleHostSelectMemo)
  //     if (otherAllSelectHostMap[value]) {
  //       return false;
  //     }
  //     return true;
  //   },
  //   message: t('业务空闲机IP重复'),
  // },
  // ];

  const editSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref('resource_pool');
  const isShowIpSelector = ref(false);
  const isShowResourcePoolSelector = ref(false);
  const countMap = reactive<Record<string, number>>({
    resource_pool: 0,
    resource_pool_manual: 0,
    manual_input: 0,
  });

  const localHostList = shallowRef<
    {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[]
  >([]);

  watch(
    () => props.clusterData,
    (newClusterData) => {
      if (newClusterData) {
        getResourceSpecList({
          limit: -1,
          spec_name: newClusterData.specConfig.name,
          spec_cluster_type: ClusterTypes.TENDBCLUSTER,
          spec_machine_type: 'spider',
          enable: true,
        }).then((specResult) => {
          if (specResult.results.length) {
            const specItem = specResult.results[0];
            getSpecResourceCount({
              bk_biz_id: currentBizId,
              bk_cloud_id: newClusterData.bkCloudId,
              spec_ids: [specItem.spec_id],
            }).then((countReuslt) => {
              countMap.resource_pool = countReuslt[specItem.spec_id];
            });
          }
        });
        // fetchList({
        //   bk_biz_id: currentBizId,
        //   limit: 0,
        //   offset: 0
        // }).then(resourceResult => {
        //   const {length} = resourceResult.results
        //   if (length !== 0) {
        //     countMap.resource_pool_manual = length
        //   }
        // })
        // getHostTopo({
        //   mode: "idle_only",
        //   all_scope: true,
        //   scope_list: [
        //     {
        //       scope_id: currentBizId,
        //       scope_type: "biz",
        //       bk_cloud_id: newClusterData.bkCloudId
        //     }
        //   ]
        // }).then(hostTopoResult => {
        //   countMap.manual_input = hostTopoResult[0].count
        // })
      }
    },
    {
      immediate: true,
    },
  );

  // const getOtherAllSelectHostMap = (hostSelectMemo: { [key: string]: Record<string, boolean> }) => {
  //   const otherHostSelectMemo = { ...hostSelectMemo };
  //   delete otherHostSelectMemo[instanceKey];
  //   return Object.values(otherHostSelectMemo).reduce((result, selectItem) => ({
  //     ...result,
  //     ...selectItem,
  //   }), {} as Record<string, boolean>);
  // }

  // const disablePoolDialogSubmitMethod = (list: DbResourceModel[]) => list.length >= 1 ? false : t('还差n台，请先勾选足够的IP', { n: 1 - list.length })

  // const disablePoolHostMethod = (data: DbResourceModel, list: DbResourceModel[]) => {
  //   const otherAllSelectHostMap = getOtherAllSelectHostMap(poolHostSelectMemo)
  //   if (otherAllSelectHostMap[data.ip]) {
  //     return t('已被其他行选中');
  //   }
  //   if (list.length >= 1) {
  //     return t('仅需n台', { n: 1 })
  //   }
  //   return false
  // }

  // const disableIdleDialogSubmitMethod = (hostList: HostInfo[]) => hostList.length === 1 ? false : t('需n台', { n: 1 });

  // const disableIdleHostMethod = (data: HostInfo, list: HostInfo[]) => {
  //   const otherAllSelectHostMap = getOtherAllSelectHostMap(idleHostSelectMemo)
  //   if (otherAllSelectHostMap[data.ip]) {
  //     return t('已被其他行选中');
  //   }
  //   if (list.length >= 1) {
  //     return t('仅需n台', { n: 1 })
  //   }
  //   return false
  // }

  // const handleIdleHostChange = (hostList: HostInfo[]) => {
  //   localHostList.value = hostList.map(hostItem => ({
  //     bk_biz_id: hostItem.biz.id,
  //     bk_cloud_id: hostItem.cloud_id,
  //     bk_host_id: hostItem.host_id,
  //     ip: hostItem.ip
  //   }));
  //   localValue.value = hostList.map(hostItem => hostItem.ip).join(',')
  // };

  // const handlePoolHostChange = (hostList: DbResourceModel[]) => {
  //   localHostList.value = hostList.map(hostItem => ({
  //     bk_biz_id: hostItem.bk_biz_id,
  //     bk_cloud_id: hostItem.bk_cloud_id,
  //     bk_host_id: hostItem.bk_host_id,
  //     ip: hostItem.ip
  //   }));
  //   localValue.value = hostList.map(hostItem => hostItem.ip).join(',')
  // }

  const handleChange = (value: string) => {
    if (value === 'manual_input') {
      isShowIpSelector.value = true;
    } else if (value === 'resource_pool_manual') {
      isShowResourcePoolSelector.value = true;
    }
    localValue.value = value;
  };

  const selectDisplayFun = (
    value: string,
    item?: {
      id: string | number;
      name: string;
    },
  ) => {
    if (item?.id === 'resource_pool') {
      return item.name;
    }
    if (['resource_pool_manual', 'manual_input'].includes(value)) {
      return '';
    }
    return value;
  };
  // onBeforeUnmount(() => {
  //   poolHostSelectMemo[instanceKey] = {};
  //   idleHostSelectMemo[instanceKey] = {};
  // });

  defineExpose<Exposes>({
    getValue() {
      const getResult = () => {
        if (props.clusterData) {
          const { clusterData } = props;
          const value = {
            cluster_id: clusterData.clusterId,
            old_slave: {
              bk_biz_id: currentBizId,
              bk_cloud_id: clusterData.bkCloudId,
              bk_host_id: clusterData.bkHostId,
              ip: clusterData.ip,
            },
          };

          const currentSelectItem = editSelectRef.value!.getCurrentItem();
          if (currentSelectItem?.id === 'resource_pool') {
            Object.assign(value, {
              resource_spec: {
                new_slave: {
                  ...clusterData.specConfig,
                  count: 1,
                  spec_id: clusterData.specConfig.id,
                },
              },
            });
          } else {
            Object.assign(value, {
              new_slave: localHostList.value[0],
            });
          }

          return value;
        }
      };
      return editSelectRef
        .value!.getValue()
        .then(() => getResult())
        .catch(() => Promise.reject(getResult()));
    },
  });
</script>

<style lang="less">
  .spec-display {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .spec-display-count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: #979ba5;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }
</style>
