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
  <div class="dumper-rule-list">
    <div class="rules-view-operations">
      <div class="row-title">
        {{ t('订阅的库表') }}
      </div>
      <div class="rules-view-operations-right">
        <DbSearchSelect
          v-model="search"
          :data="searchSelectData"
          :placeholder="t('请输入DB/表名')"
          style="width: 500px;"
          @change="handleLocalSearch" />
      </div>
    </div>
    <BkTable
      class="subscribe-table"
      :columns="subscribeColumns"
      :data="subscribeTableData" />
    <div
      class="row-title"
      style="margin-top: 35px;margin-bottom: 16px;">
      {{ t('数据源与接收端') }}
    </div>
    <BkButton
      style="margin-bottom: 16px;"
      @click="handleAppendInstance">
      {{ t('追加订阅') }}
    </BkButton>
    <BkTable
      class="subscribe-table"
      :columns="receiverColumns"
      :data="receiverTableData" />
    <div
      class="info-item"
      style="margin-top: 20px;margin-bottom: 15px;">
      {{ t('部署位置') }}：<span class="content">{{ t('集群Master所在主机') }}</span>
    </div>
  </div>
  <AppendSubscribeSlider
    v-model="showAppendSubscribeSlider"
    :data="data" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { listDumperConfig } from '@services/source/dumper';

  import { getSearchSelectorParams } from '@utils';

  import AppendSubscribeSlider from './append-subscribe/Index.vue';

  interface Props {
    data: DumperConfig | null
  }

  type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number]

  const props = defineProps<Props>();

  const { t } = useI18n();

  const search = ref([]);
  const showAppendSubscribeSlider = ref(false);
  const subscribeTableData = ref<DumperConfig['repl_tables']>([]);
  const receiverTableData = ref<DumperConfig['dumper_instances']>([]);

  let subscribeRawTableData: DumperConfig['repl_tables'] = [];

  const syncTypeMap = {
    full_sync: t('全量同步'),
    incr_sync: t('增量同步'),
  } as Record<string, string>;

  const searchSelectData = [
    {
      name: 'DB',
      id: 'db_name',
    },
    {
      name: t('表名'),
      id: 'table_name',
    },
  ];

  const subscribeColumns = [
    {
      label: t('DB 名'),
      field: 'db_name',
      width: 300,
    },
    {
      label: t('表名'),
      field: 'table_names',
      minWidth: 100,
      render: ({ data }: {data: { table_names: string[] }}) => (
        <div class="table-names-box">
          {
            data.table_names.map((item, index) => <div key={index} class="name-item">{ item }</div>)
          }
        </div>
      ),
    },
  ];

  const receiverColumns = [
    {
      label: t('数据源集群'),
      field: 'source_cluster_domain',
    },
    {
      label: t('部署dumper实例ID'),
      field: 'dumper_id',
    },
    {
      label: t('接收端类型'),
      field: 'protocol_type',
    },
    {
      label: t('接收端集群与端口'),
      field: 'target_address',
    },
    {
      label: t('同步方式'),
      field: 'add_type',
      render: ({ data }: {data: { add_type: string }}) => <span>{syncTypeMap[data.add_type]}</span>,
    },
  ];

  watch(() => props.data, (data) => {
    if (data) {
      subscribeRawTableData = data.repl_tables;
      subscribeTableData.value = data.repl_tables;
      receiverTableData.value = data.dumper_instances;
    }
  }, {
    immediate: true,
  });

  const handleAppendInstance = () => {
    showAppendSubscribeSlider.value = true;
  };

  const handleLocalSearch = () => {
    const searchParams = getSearchSelectorParams(search.value);
    const { db_name: dbName, table_name: tableName } = searchParams as { db_name?: string, table_name?: string };
    subscribeTableData.value = subscribeRawTableData.filter(item => (!dbName || new RegExp(dbName).test(item.db_name))
      && (!tableName || item.table_names.some(name => new RegExp(tableName).test(name))));
  };
</script>

<style lang="less" scoped>
.dumper-rule-list {
  height: 100%;
  background-color: white;

  .row-title {
    font-size: 14px;
    font-weight: 700;
    color: #313238;
  }

  .subscribe-table {
    :deep(.table-names-box) {
      display: flex;
      width: 100%;
      flex-wrap: wrap;
      padding-top: 10px;
      padding-bottom: 2px;

      .name-item {
        height: 22px;
        padding: 0 8px;
        margin-right: 4px;
        margin-bottom: 8px;
        line-height: 22px;
        color: #63656E;
        background: #F0F1F5;
        border-radius: 2px;
      }
    }

    :deep(th) {
      .head-text {
        color: #313238;
      }
    }
  }

  .info-item {
    font-size: 12px;
    color: #63656E;

    .content {
      color: #313238;
    }
  }

  .rules-view-header {
    display: flex;
    height: 20px;
    color: @title-color;
    align-items: center;

    .rules-view-header-icon {
      font-size: 18px;
      color: @gray-color;
    }
  }

  .rules-view-operations {
    display: flex;
    align-items: center;
    padding: 16px 0;


    .rules-view-operations-right {
      flex: 1;
      display: flex;
      justify-content: flex-end;
    }

    .bk-button {
      margin-right: 8px;
    }

    .dropdown-button {
      .dropdown-button-icon {
        margin-left: 6px;
        transition: all 0.2s;
      }

      &.active:not(.is-disabled) {
        .dropdown-button-icon {
          transform: rotate(180deg);
        }
      }
    }
  }

  .instance-box {
    display: flex;
    align-items: flex-start;
    padding: 8px 0;
    overflow: hidden;

    .instance-name {
      line-height: 20px;
    }

    .cluster-tags {
      display: flex;
      margin-left: 4px;
      align-items: center;
      flex-wrap: wrap;
    }

    .cluster-tag {
      margin: 2px;
      flex-shrink: 0;
    }

    .db-icon-copy {
      display: none;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }

  .is-offline {
    a {
      color: @gray-color;
    }

    .cell {
      color: @disable-color;
    }
  }
}

.bk-dropdown-item {
  &.is-disabled {
    color: @disable-color;
    cursor: not-allowed;
  }
}
</style>
