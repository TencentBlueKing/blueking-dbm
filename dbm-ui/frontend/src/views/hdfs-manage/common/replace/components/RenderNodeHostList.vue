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
  <div class="hsfs-replace-render-host-list">
    <DbOriginalTable
      class="mt16"
      :columns="columns"
      :data="localList" />
    <div
      v-show="isEmpty"
      class="add-new-box"
      :class="{
        'is-empty': isEmpty
      }">
      <IpSelector
        :biz-id="currentBizId"
        :cloud-info="cloudInfo"
        :disable-dialog-submit-method="disableDialogSubmitMethod"
        :show-view="false"
        @change="handleIpListChange">
        <template #submitTips="{ hostList }">
          <I18nT
            keypath="需n台_已选n台"
            style="font-size: 14px; color: #63656e;"
            tag="span">
            <span style="font-weight: bold; color: #2dcb56;"> {{ localList.length }} </span>
            <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
          </I18nT>
        </template>
      </IpSelector>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import {
    computed,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import type {
    HostDetails,
  } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  interface ILocalNode {
    old_ip: string,
    old_bk_host_id: number,
    old_bk_cloud_id: number,
    old_machine_type: string,
    ip: string,
    bk_host_id: number,
    bk_cloud_id: number,
    bk_cloud_name: string,
    machine_type: string,
  }

  interface Props {
    data: Array<HdfsNodeModel>
  }

  interface Exposes {
    getValue: () => Array<ILocalNode>
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const columns = [
    {
      label: t('新节点IP'),
      field: 'ip',
      width: 240,
    },
    {
      label: t('被替换的节点IP'),
      field: 'old_ip',
    },
    {
      label: t('机型'),
      field: 'old_machine_type',
      render: ({ data }: {data:ILocalNode}) => data.old_machine_type || '--',
    },
    {
      label: t('操作'),
      width: 80,
      render: ({ data }: {data:ILocalNode}) => (
          <bk-button
            theme="primary"
            text
            onClick={() => handleRemove(data)}>
            { t('移除') }
          </bk-button>
      ),
    },
  ];

  const localList = shallowRef<Array<ILocalNode>>([]);
  const isEmpty = computed(() => !localList.value[0].ip);
  const cloudInfo = computed(() => {
    const [firstItem] = localList.value;
    if (firstItem) {
      return {
        id: firstItem.bk_cloud_id,
        name: firstItem.bk_cloud_name,
      };
    }
    return {};
  });

  watch(() => props.data, () => {
    localList.value = props.data.map(item => ({
      old_ip: item.ip,
      old_bk_host_id: item.bk_host_id,
      old_bk_cloud_id: item.bk_cloud_id,
      old_machine_type: item.machine_type,
      ip: '',
      bk_host_id: 0,
      bk_cloud_id: item.bk_cloud_id,
      bk_cloud_name: item.bk_cloud_name,
      machine_type: item.machine_type,
    }));
  }, {
    immediate: true,
  });

  const disableDialogSubmitMethod = (hostList: Array<any>) => (
    hostList.length === localList.value.length
      ? false
      : t('需n台', { n: props.data.length })
  );

  // 添加新IP
  const handleIpListChange = (hostList: Array<HostDetails>) => {
    window.changeConfirm = true;
    localList.value = hostList.reduce((result, item, index) => {
      const localNode = localList.value[index];
      result.push({
        ...localNode,
        ...item,
        ip: item.ip,
        bk_host_id: item.host_id,
        bk_cloud_id: item.cloud_id,
        machine_type: localNode.old_machine_type,
      });
      return result;
    }, [] as Array<ILocalNode>);
  };

  const handleRemove = (node: ILocalNode) => {
    window.changeConfirm = true;
    localList.value = localList.value.reduce((result, item) => {
      if (item.bk_host_id !== node.bk_host_id) {
        result.push(item);
      }
      return result;
    }, [] as Array<ILocalNode>);
  };

  defineExpose<Exposes>({
    getValue() {
      if (isEmpty.value) {
        return [];
      }
      return localList.value;
    },
  });
</script>
<style lang="less" scoped>
  .hsfs-replace-render-host-list {
    position: relative;

    &:hover {
      .add-new-box {
        display: flex !important;
        background-color: rgb(245 247 250 / 81%);

        &.is-empty {
          background: #fff;
        }
      }
    }

    .add-new-box {
      position: absolute;
      top: 43px;
      bottom: 1px;
      left: 0;
      display: flex;
      width: 240px;
      background: #fff;
      align-items: center;
      justify-content: center;
    }
  }
</style>
