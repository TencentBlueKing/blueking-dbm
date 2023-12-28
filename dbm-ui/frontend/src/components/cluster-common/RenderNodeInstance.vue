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
  <div class="render-cluster-node-instance">
    <div>
      <div
        v-for="(item, index) in renderList"
        :key="`${item.ip}:${item.port}`"
        :class="{
          'is-unavailable': item.status === 'unavailable'
        }">
        <span>{{ item.ip }}:{{ item.port }}</span>
        <span
          v-if="item.status === 'unavailable'"
          class="unavailable-flag">
          <span class="unavailable-flag-text">{{ $t('不可用') }}</span>
        </span>
        <template v-if="index === 0">
          <BkPopover
            ext-cls="copy-popover"
            placement="top"
            theme="light">
            <DbIcon
              type="copy" />
            <template #content>
              <a
                class="copy-trigger"
                href="javescript:"
                @click="handleCopyAllIps">
                {{ $t('复制IP') }}
              </a>
              <span class="copy-trigger-split" />
              <a
                class="copy-trigger"
                href="javescript:"
                @click="handleCopyAll">
                {{ $t('复制实例') }}
              </a>
            </template>
          </BkPopover>
        </template>
      </div>
      <span v-if="originalList.length < 1">--</span>
    </div>
    <BkButton
      v-if="isNeedShowMore"
      key="button"
      text
      theme="primary"
      @click="handleShowMore">
      {{ $t('查看更多') }}
    </BkButton>
    <BkDialog
      class="cluster-node-instance-dialog"
      :is-show="isShowMore"
      :title="$t('xx预览', { name: title })"
      width="1000"
      @closed="handleHideMore">
      <div class="action-box">
        <BkButton
          class="mr8"
          @click="handleCopyAbnormal">
          {{ $t('复制异常实例') }}
        </BkButton>
        <BkButton
          class="mr8"
          @click="handleCopyListAll">
          {{ $t('复制全部实例') }}
        </BkButton>
        <BkInput
          v-model="search"
          clearable
          :placeholder="$t('请输入实例_enter进行搜索')"
          type="search"
          @clear="handleSearch"
          @enter="handleSearch" />
      </div>
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="dataSource"
        releate-url-query
        style="margin-bottom: 34px;" />
      <template #footer>
        <BkButton @click="handleHideMore">
          {{ $t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>
<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import {
    computed,
    nextTick,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import RenderInstanceStatus from '@components/cluster-common/RenderInstanceStatus.vue';
  import RenderClusterRole from '@components/cluster-common/RenderRole.vue';

  import { messageWarn } from '@utils';

  interface Props {
    title: string,
    role: string,
    clusterId: number,
    originalList: Array<{ip: string, port: number, status: 'running' | 'unavailable'}>;
    dataSource: (params: any)=> Promise<any>,
  }

  interface ITableData {
    status: string,
    instance_address: string,
    role: string,
  }

  const props = defineProps<Props>();

  const maxRenderNum = 3;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const tableRef = ref();
  const isShowMore = ref(false);
  const renderList = computed(() => props.originalList.slice(0, maxRenderNum));
  const isNeedShowMore =  computed(() => props.originalList.length > maxRenderNum);
  const search = ref('');

  const copy = useCopy();

  const columns: InstanceType<typeof Table>['$props']['columns'] = [
    {
      label: t('实例'),
      field: 'instance_address',
    },
    {
      label: t('部署角色'),
      field: 'role',
      render: ({ data }: { data: ITableData }) => <RenderClusterRole data={[data.role]} />,
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data }: { data: ITableData }) => <RenderInstanceStatus data={data.status} />,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
    },
  ];

  // 显示实例详情
  const handleShowMore = () => {
    isShowMore.value = true;
    nextTick(() => {
      tableRef.value.fetchData({
        bk_biz_id: currentBizId,
        cluster_id: props.clusterId,
        role: props.role,
      });
    });
  };

  const handleSearch = () => {
    tableRef.value.fetchData({
      bk_biz_id: currentBizId,
      cluster_id: props.clusterId,
      role: props.role,
      instance_address: search.value,
      offset: 0,
    });
  };

  const handleHideMore = () => {
    isShowMore.value = false;
  };

  const handleCopyAllIps = () => {
    const ips = [...new Set(props.originalList.map(item => item.ip))];
    if (ips.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    copy(ips.join('\n'));
  };

  const handleCopyAll = () => {
    const instances = props.originalList.map(item => `${item.ip}:${item.port}`);
    if (instances.length < 1) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(instances.join('\n'));
  };

  // 复制异常实例
  const handleCopyAbnormal = () => {
    const abnormalInstances = (tableRef.value.getData() as Array<ITableData>).reduce((result, item) => {
      if (item.status === 'failed') {
        result.push(item.instance_address);
      }
      return result;
    }, [] as Array<string>);
    if (abnormalInstances.length < 1) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(abnormalInstances.join('\n'));
  };

  // 复制所有实例
  const handleCopyListAll = () => {
    const instances = (tableRef.value.getData() as Array<ITableData>).map(item => item.instance_address);
    if (instances.length < 1) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(instances.join('\n'));
  };
</script>
<style lang="less">
.render-cluster-node-instance {
  position: relative;
  display: inline-block;
  padding-bottom: 10px;
  margin-top: 10px;
  line-height: 20px;

  .is-unavailable {
    color: #c4c6cc;
  }

  .unavailable-flag {
    display: inline-flex;
    height: 16px;
    padding: 0 2px;
    margin-left: 2px;
    color: #63656e;
    background: #f0f1f5;
    border-radius: 2px;
    align-items: center;

    .unavailable-flag-text {
      font-size: 12px;
      transform: scale(0.8341);
    }
  }
}

.cluster-node-instance-dialog {
  .bk-dialog-header {
    padding: 18px 24px 24px !important;
    line-height: 1;
  }

  .action-box {
    display: flex;
    margin-bottom: 12px;
  }
}

.copy-popover {
  padding: 4px 6px !important;

  .bk-pop2-arrow {
    display: none;
  }

  .copy-trigger {
    display: inline-block;
    padding: 0 4px;
    font-size: 12px;
    line-height: 24px;
    vertical-align: middle;
    border-radius: 2px;

    &:hover {
      background-color: #F0F1F5;
    }
  }

  .copy-trigger-split {
    display: inline-block;
    width: 1px;
    height: 18px;
    margin: 0 4px;
    vertical-align: middle;
    background-color: #F0F1F5;
  }
}
</style>
