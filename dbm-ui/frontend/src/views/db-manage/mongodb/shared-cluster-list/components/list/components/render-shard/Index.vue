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
  <div class="cluster-shard">
    <div
      v-for="(item, index) in data"
      :key="index">
      <RenderRow
        class="mb-4"
        :data="item.instanceList">
        <template #prefix>
          <span>{{ item.shardName }}:/</span>
        </template>
      </RenderRow>
    </div>
    <span v-if="renderData.length < 1"> -- </span>
    <BkButton
      v-if="hasMore"
      text
      theme="primary"
      @click="handleShowMore">
      {{ t('查看更多') }}
    </BkButton>
  </div>
  <BkDialog
    v-model:is-show="isDialogShow"
    class="cluster-shard-dialog"
    :title="title"
    :width="1100"
    @closed="handleClose">
    <div class="cluster-shard-content">
      <div class="cluster-shard-content-operations mb-16">
        <BkButton
          class="mr-8"
          @click="handleCopyAbnormal">
          {{ t('复制异常实例') }}
        </BkButton>
        <BkButton
          class="mr-8"
          @click="handleCopyAll">
          {{ t('复制所有实例') }}
        </BkButton>
        <BkInput
          v-model="keyword"
          class="keyword-input"
          clearable
          :placeholder="t('请输入实例')"
          type="search"
          @clear="filterInstance"
          @enter="filterInstance" />
      </div>
      <DbOriginalTable
        ref="tableRef"
        :columns="columns"
        :data="tableList"
        :max-height="440"
        :pagination="pagination"
        @clear-search="handleClearSearch"
        @page-limit-change="handleTableLimitChange" />
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import { ClusterInstStatusKeys } from '@common/const';

  import { execCopy, messageWarn } from '@utils';

  import RenderRow from './components/RenderRow.vue';

  interface Props {
    title: string;
    data: {
      shardName: string;
      instanceList: string[];
    }[];
    instanceList: MongodbModel['mongodb']
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const isDialogShow = ref(false)
  const keyword = ref('')
  const pagination = reactive({
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100, 500],
  });

  const tableList = shallowRef<Props['data']>([])

  const MAX_COUNT = 3

  const columns = [
    {
      label: t('ShardSvr 名称'),
      field: 'shardName',
      width: 200,
    },
    {
      label: t('实例'),
      field: 'instanceList',
      showOverflowTooltip: false,
      render: ({ data }: { data: Props['data'][number] }) => <RenderRow data={data.instanceList} />
      },
  ];

  watch(() => props.data,() => {
    tableList.value = props.data
  }, {
    immediate: true
  })

  const renderData = computed(() => props.data.slice(0, MAX_COUNT));
  const hasMore = computed(() => props.data.length > MAX_COUNT);

  const handleShowMore = () => {
    isDialogShow.value = true;
  };

  const handleClearSearch = () => {
    keyword.value = '';
  };

  const handleTableLimitChange = () => {
    pagination.current = 1;
  }

  /**
   * 复制异常实例
   */
  const handleCopyAbnormal = () => {
    const abnormalInstances = props.instanceList
      .filter((item) => item.status !== ClusterInstStatusKeys.RUNNING)
      .map((item) => item.instance);
    if (abnormalInstances.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(abnormalInstances.join('\n'), t('复制成功，共n条', { n: abnormalInstances.length }));
  };

  /**
   * 复制所有实例
   */
  const handleCopyAll = () => {
    const instances = props.instanceList.map((item) => item.instance);
    if (instances.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(instances.join('\n'), t('复制成功，共n条', { n: instances.length }));
  };

  const filterInstance = () => {
    if (keyword.value) {
      tableList.value = props.data.reduce<Props['data']>((prev, item) => {
        const filterInstanceList = item.instanceList.filter(instanceItem => instanceItem.includes(keyword.value))
        if (filterInstanceList.length) {
          prev.push({
            shardName: item.shardName,
            instanceList: filterInstanceList
          })
        }
        return prev
      }, [])
      return
    }
    tableList.value = props.data
  }

  const handleClose = () => {
    isDialogShow.value = false;
    keyword.value = '';
    tableList.value = props.data;
  };
</script>

<style lang="less" scoped>
  .cluster-shard {
    padding: 8px 0;

    .cluster-shard-more {
      display: inline-block;
      margin-top: 2px;
    }

    .cluster-shard-dialog {
      width: 80%;
      max-width: 1600px;
      min-width: 1200px;
    }
  }

  .cluster-shard-content {
    .cluster-shard-content-operations {
      display: flex;
      align-items: center;

      .keyword-input {
        flex: 1;
      }
    }
  }
</style>
