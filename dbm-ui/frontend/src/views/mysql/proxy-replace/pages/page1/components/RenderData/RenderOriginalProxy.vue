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
  <div
    class="render-original-proxy"
    :class="{
      'is-editing': isShowEdit
    }">
    <TableEditInput
      v-if="isShowEdit"
      ref="editRef"
      v-model="localInstanceAddress"
      multi-input
      :placeholder="$t('请输入IP_Port_使用换行分割一次可输入多个')"
      :rules="rules"
      @multi-input="handleMultiInput"
      @submit="handleEditSubmit" />
    <template v-else>
      <div
        class="render-cluster-domain"
        @click="handleShowEdit">
        <span>{{ localInstanceAddress }}</span>
        <div
          v-if="isRelateLoading"
          class="relate-loading">
          <DbIcon type="sync-pending" />
        </div>
        <div
          v-else
          ref="handlerRef"
          class="relate-btn">
          <DbIcon type="associated" />
        </div>
      </div>
      <div
        v-if="selectRelateClusterList.length > 0"
        class="related-cluster-list">
        <div
          v-for="item in selectRelateClusterList"
          :key="item.id">
          -- {{ item.master_domain }}
        </div>
      </div>
    </template>
    <div style="display: none;">
      <div
        ref="popRef"
        style="padding: 9px 7px;">
        <BkLoading :loading="isRelateLoading">
          <div style="margin-bottom: 8px; font-size: 12px; line-height: 16px;">
            <span style="font-weight: bold; color: #313238;">{{ $t('同机关联集群') }}</span>
            <span style="color: #63656e;">{{ $t('同主机关联的其他集群_勾选后一同替换') }}</span>
          </div>
          <div style="max-height: 300px; overflow: auto;">
            <template v-if="relatedClusterList.length > 0">
              <div
                v-for="item in relatedClusterList"
                :key="item.id"
                style="padding: 8px 0;">
                <BkCheckbox
                  label
                  :model-value="Boolean(realateCheckedMap[item.id])"
                  @change="(value: boolean) => handleRelateCheckChange(item, value)">
                  {{ item.master_domain }}
                </BkCheckbox>
              </div>
            </template>
            <p
              v-else
              style="color: #63656e;">
              {{ $t('无同机关联集群') }}
            </p>
          </div>
        </BkLoading>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  const instanceAddreddMemo: { [key: string]: Record<string, boolean> } = {};

</script>
<script setup lang="ts">
  import _ from 'lodash';
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { checkInstances } from '@services/clusters';
  import { findRelatedClustersByClusterIds } from '@services/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  import { random } from '@utils';

  import type { IProxyData } from './Row.vue';

  interface Props {
    modelValue?: IProxyData,
  }

  interface Emits {
    (e: 'inputCreate', value: Array<string>): void,
  }

  interface Exposes {
    getValue: () => Array<number>
  }

  interface IClusterData {
    id: number,
    master_domain: string,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const instanceKey = `render_original_proxy_${random()}`;
  instanceAddreddMemo[instanceKey] = {};
  let proxyInstanceMemo = {} as IProxyData;

  let tippyIns: Instance | undefined;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();
  const handlerRef = ref();
  const popRef = ref();

  const localClusterId = ref(0);
  const localInstanceAddress = ref('');
  const isShowEdit = ref(true);
  const isRelateLoading = ref(false);
  const relatedClusterList = shallowRef<Array<IClusterData>>([]);
  const realateCheckedMap = shallowRef<Record<number, IClusterData>>({});
  const selectRelateClusterList = shallowRef<Array<IClusterData>>([]);

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标Proxy不能为空'),
    },
    {
      validator: () => checkInstances(currentBizId, {
        instance_addresses: [localInstanceAddress.value],
      }).then((data) => {
        if (data.length < 1) {
          return false;
        }
        instanceAddreddMemo[instanceKey][localInstanceAddress.value] = true;

        const [currentInstanceData] = data;
        proxyInstanceMemo = currentInstanceData;
        localClusterId.value = currentInstanceData.cluster_id;
        return true;
      }),
      message: t('目标Proxy不存在'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = instanceAddreddMemo[instanceKey];
        const otherClusterMemoMap = { ...instanceAddreddMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce((result, item) => ({
          ...result,
          ...item,
        }), {} as Record<string, boolean>);

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('目标Proxy重复'),
    },
  ];

  // 通过 ID 获取关联集群
  const fetchRelatedClustersByClusterIds = () => {
    isRelateLoading.value = true;
    findRelatedClustersByClusterIds({
      cluster_ids: [localClusterId.value],
      bk_biz_id: currentBizId,
    }).then((data) => {
      if (data.length < 1) {
        return;
      }
      const clusterData = data[0];
      relatedClusterList.value = clusterData.related_clusters;
      // 默认选中所有关联集群
      realateCheckedMap.value = clusterData.related_clusters.reduce((result, item) => ({
        ...result,
        [item.id]: item,
      }), {} as Record<number, IClusterData>);
      selectRelateClusterList.value = Object.values(realateCheckedMap.value);

      setTimeout(() => {
        initRelateClusterPopover();
      });
    })
      .finally(() => {
        isRelateLoading.value = false;
      });
  };

  // 初始化管理集群 Popover
  const initRelateClusterPopover = () => {
    if (!handlerRef.value) {
      return;
    }

    // 使用 v-if 导致 ref 变化，这里需要重新生成 tippyInst
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }

    tippyIns = tippy(handlerRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom',
      appendTo: () => document.body,
      theme: 'light',
      maxWidth: 'none',
      trigger: 'click',
      interactive: true,
      arrow: true,
      offset: [0, 8],
      zIndex: 999999,
      onHide() {
        selectRelateClusterList.value = Object.values(realateCheckedMap.value);
      },
    });
  };

  // 同步外部值
  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      proxyInstanceMemo = props.modelValue;
      localClusterId.value = props.modelValue.cluster_id;
      localInstanceAddress.value = props.modelValue.instance_address;

      instanceAddreddMemo[instanceKey][localInstanceAddress.value] = true;

      isShowEdit.value = !props.modelValue.instance_address;
    }
  }, {
    immediate: true,
  });

  // 获取关联集群
  watch(localClusterId, () => {
    if (!localClusterId.value) {
      return;
    }

    fetchRelatedClustersByClusterIds();
  }, {
    immediate: true,
  });

  // 切换编辑状态
  const handleShowEdit = () => {
    isShowEdit.value = true;
    nextTick(() => {
      editRef.value.focus();
    });
  };

  // 提交编辑
  const handleEditSubmit = () => {
    isShowEdit.value = false;
    nextTick(() => {
      initRelateClusterPopover();
    });
  };

  const handleMultiInput = (list: Array<string>) => {
    emits('inputCreate', list);
  };

  // 选中关联集群
  const handleRelateCheckChange = (clusterData: IClusterData, checked: boolean) => {
    const checkedMap = { ...realateCheckedMap.value };
    if (checked) {
      checkedMap[clusterData.id] = clusterData;
    } else {
      delete checkedMap[clusterData.id];
    }
    realateCheckedMap.value = checkedMap;
  };

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
    delete instanceAddreddMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      const {
        bk_host_id,
        bk_cloud_id,
        ip,
        port,
      } = proxyInstanceMemo;

      const clusterIds = _.uniq([
        localClusterId.value,
        ...Object.values(realateCheckedMap.value).map(item => item.id),
      ]);

      const result = {
        cluster_ids: clusterIds,
        origin_proxy: {
          bk_biz_id: currentBizId,
          bk_host_id,
          bk_cloud_id,
          ip,
          port,
        },
      };

      // 用户输入未完成验证
      if (editRef.value) {
        return editRef.value
          .getValue()
          .then(() => result);
      }
      // 用户输入错误
      if (!localClusterId.value) {
        return Promise.reject();
      }
      return Promise.resolve(result);
    },
  });
</script>
<style lang="less" scoped>
  @keyframes rotate-loading {
    0% {
      transform: rotateZ(0);
    }

    100% {
      transform: rotateZ(360deg);
    }
  }

  .render-original-proxy {
    position: relative;
    padding: 10px 0;

    &.is-editing {
      padding: 0;
    }

    .render-cluster-domain {
      display: flex;
      height: 20px;
      padding-left: 16px;
      line-height: 20px;
      align-items: center;

      .relate-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-left: 4px;
        color: #3a84ff;
        animation: rotate-loading 1s linear infinite;
      }

      .relate-btn {
        display: flex;
        width: 20px;
        height: 20px;
        margin-left: 4px;
        color: #3a84ff;
        cursor: pointer;
        background: #e1ecff;
        border-radius: 2px;
        align-items: center;
        justify-content: center;
      }
    }

    .related-cluster-list {
      padding-left: 24px;
      font-size: 12px;
      line-height: 22px;
      color: #979ba5;
    }
  }
</style>
