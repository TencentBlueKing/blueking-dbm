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
    class="render-host-box"
    @mouseenter="handleControlShowEdit(true)"
    @mouseleave="handleControlShowEdit(false)">
    <BkPopover
      :is-show="isShowOverflowTip"
      placement="top"
      :popover-delay="0"
      theme="light"
      trigger="manual">
      <TableEditInput
        ref="inputRef"
        class="host-input"
        :disabled="localHostList.length === 0"
        :model-value="localHostList.map(item => item.ip).join(',  ')"
        :placeholder="t('请选择主机')"
        readonly
        :rules="rules"
        textarea
        @overflow-change="handleOverflow" />
      <template #content>
        <div
          v-for="item in localHostList"
          :key="item.ip">
          {{ item.ip }}
        </div>
      </template>
    </BkPopover>

    <BkPopover
      v-if="!!clusterData && showEditIcon"
      :content="t('从业务拓扑选择')"
      placement="top"
      theme="dark">
      <div
        class="edit-btn"
        @click="handleShowIpSelector">
        <DbIcon type="host-select" />
      </div>
    </BkPopover>
  </div>
  <IpSelector
    v-if="clusterData"
    v-model:show-dialog="isShowIpSelector"
    :biz-id="clusterData.bk_biz_id"
    button-text=""
    :cloud-info="{
      id: clusterData.bk_cloud_id,
      name: clusterData.bk_cloud_name
    }"
    :data="localHostList"
    service-mode="all"
    :show-view="false"
    @change="handleHostChange" />
</template>
<script setup lang="ts">
  import {
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type SpiderModel from '@services/model/spider/spider';
  import type { HostDetails } from '@services/types/ip';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  interface Props {
    clusterData?: SpiderModel
  }

  interface Exposes {
    getValue: () => Promise<Array<string>>
  }

  defineProps<Props>();

  const { t } = useI18n();
  const inputRef = ref();
  const isShowIpSelector = ref(false);
  const showEditIcon = ref(false);
  const isOverflow = ref(false);

  const isShowOverflowTip = computed(() => isOverflow.value && showEditIcon.value);
  const localHostList = shallowRef<HostDetails[]>([]);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('运维节点 IP 不能为空'),
    },
  ];

  const handleOverflow = (status: boolean) => {
    isOverflow.value = status;
  };

  const handleControlShowEdit = (isShow: boolean) => {
    showEditIcon.value = isShow;
  };

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleHostChange = (hostList: HostDetails[]) => {
    localHostList.value = hostList;
  };

  defineExpose<Exposes>({
    getValue() {
      const formatHost = (hostList: HostDetails[]) => hostList.map(item => ({
        bk_host_id: item.host_id,
        ip: item.ip,
        bk_cloud_id: item.cloud_area.id,
      }));

      return inputRef.value
        .getValue()
        .then(() => Promise.resolve({
          spider_ip_list: formatHost(localHostList.value),
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;
    display: flex;
    align-items: center;
    overflow: hidden;
    border: 1px solid transparent;

    &:hover {
      border-color: #a3c5fd;
    }

    .host-input{
      flex: 1;

      &:hover {
        cursor: pointer;
      }
    }

    .edit-btn{
      display: flex;
      width: 24px;
      height: 24px;
      cursor: pointer;
      border-radius: 2px;
      align-items: center;
      justify-content: center;

      &:hover {
        background: #F0F1F5;
      }
    }
  }
</style>
