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
    class="render-cluster-width-relate-cluster"
    :class="{
      'is-editing': isShowEdit
    }">
    <TableEditInput
      v-show="isShowEdit"
      ref="editRef"
      v-model="localDomain"
      multi-input
      placeholder="请输入集群，使用换行分割一次可输入多个"
      :rules="rules"
      @multi-input="handleMultiInput"
      @submit="handleEditSubmit" />
    <div v-show="!isShowEdit">
      <div
        class="render-cluster-domain"
        @click="handleShowEdit">
        <span>{{ localDomain }}</span>
        <div
          v-if="isRelateLoading"
          class="relate-loading">
          <DbIcon type="sync-pending" />
        </div>
        <div
          v-else
          ref="handlerRef"
          class="relate-btn"
          @click.stop="handleShowRelateMemu">
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
    </div>
    <div style="display: none;">
      <div
        ref="popRef"
        style="padding: 9px 7px;">
        <BkLoading
          v-if="isShowRelateMemo"
          :loading="isRelateLoading">
          <div style="margin-bottom: 8px; font-size: 12px; line-height: 16px;">
            <span style="font-weight: bold; color: #313238;">同机关联集群</span>
            <span style="color: #63656e;">（{{ relateClusterTips }}）</span>
          </div>
          <div style="max-height: 300px; overflow: auto;">
            <template v-if="relatedClusterList.length > 0">
              <div
                v-for="item in relatedClusterList"
                :key="item.id"
                style="padding: 8px 0;">
                <BkCheckbox
                  :lbale="item.id"
                  :model-value="Boolean(realateCheckedMap[item.id])"
                  @change="(value: boolean) => handleRelateCheckChange(item, value)">
                  {{ item.master_domain }}
                </BkCheckbox>
              </div>
            </template>
            <p
              v-else
              style="color: #63656e;">
              无同机关联集群
            </p>
          </div>
        </BkLoading>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
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

  import {
    findRelatedClustersByClusterIds,
    queryClusters,
  } from '@services/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  import { random } from '@utils';

  interface Props {
    modelValue?: {
      id: number,
      domain: string,
      cloudId: number | null
    },
    relateClusterTips?: string
  }

  interface Emits {
    (e: 'inputCreate', value: Array<string>): void,
    (e: 'idChange', value: { id: number, cloudId: number | null }): void,
  }

  interface Exposes {
    getValue: () => Array<number>
  }

  interface IClusterData {
    id: number,
    master_domain: string,
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    relateClusterTips: '同主机关联的其他集群，勾选后一同克隆',
  });
  const emits = defineEmits<Emits>();

  const instanceKey = `render_cluster_instance_${random()}`;
  clusterIdMemo[instanceKey] = {};

  let tippyIns: Instance | undefined;

  const { currentBizId } = useGlobalBizs();

  const editRef = ref();
  const handlerRef = ref();
  const popRef = ref();

  const localClusterId = ref(0);
  const localDomain = ref('');
  const isShowEdit = ref(true);
  const isShowRelateMemo = ref(false);
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
        emits('idChange', {
          id: 0,
          cloudId: null,
        });
        return false;
      },
      message: '目标集群不能为空',
    },
    {
      validator: (value: string) => queryClusters({
        cluster_filters: [
          {
            immute_domain: value,
          },
        ],
        bk_biz_id: currentBizId,
      }).then((data) => {
        if (data.length > 0) {
          localClusterId.value = data[0].id;
          emits('idChange', {
            id: localClusterId.value,
            cloudId: data[0].bk_cloud_id,
          });
          return true;
        }
        emits('idChange', {
          id: 0,
          cloudId: null,
        });
        return false;
      }),
      message: '目标集群不存在',
    },
    {
      validator: () => {
        const currentClusterSelectMap = clusterIdMemo[instanceKey];
        const otherClusterMemoMap = { ...clusterIdMemo };
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
      message: '目标集群重复',
    },
  ];

  // const checkRelateDisable = (clusterData: IClusterData) => {
  //   const otherClusterMemoMap = { ...clusterIdMemo };
  //   delete otherClusterMemoMap[instanceKey];
  //   const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce((result, item) => ({
  //     ...result,
  //     ...item,
  //   }), {} as Record<string, boolean>);
  //   console.log(otherClusterMemoMap, clusterData);
  //   return otherClusterIdMap[clusterData.id];
  // };

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
      zIndex: 999,
      onHide() {
        selectRelateClusterList.value = Object.values(realateCheckedMap.value);
        isShowRelateMemo.value = false;
      },
    });
  };

  // 同步外部值
  watch(() => props.modelValue, () => {
    const {
      id = 0,
      domain = '',
    } = props.modelValue || {};
    localClusterId.value = id;
    localDomain.value = domain;
    isShowEdit.value = !id;
  }, {
    immediate: true,
  });

  // 获取关联集群
  watch(localClusterId, () => {
    if (!localClusterId.value) {
      return;
    }
    clusterIdMemo[instanceKey][localClusterId.value] = true;
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

  // 显示管理集群列表
  const handleShowRelateMemu = () => {
    console.log('handleShowRelateMemu');
    isShowRelateMemo.value = true;
  };

  const handleMultiInput = (list: Array<string>) => {
    emits('inputCreate', list);
  };

  // 选中关联集群
  const handleRelateCheckChange = (clusterData: IClusterData, checked: boolean) => {
    const checkedMap = { ...realateCheckedMap.value };
    if (checked) {
      checkedMap[clusterData.id] = clusterData;
      clusterIdMemo[instanceKey][clusterData.id] = true;
    } else {
      delete checkedMap[clusterData.id];
      delete clusterIdMemo[instanceKey][clusterData.id];
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
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      const result = {
        cluster_ids: _.uniq([
          localClusterId.value,
          ...Object.values(realateCheckedMap.value).map(item => item.id),
        ]),
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

  .render-cluster-width-relate-cluster {
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
