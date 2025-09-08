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
  <EditableColumn
    :disabled-method="disabledMethod"
    field="db_list"
    :label="t('最终DB')"
    :loading="loading"
    :min-width="200"
    required
    :rules="rules">
    <EditableBlock :placeholder="t('自动生成')">
      <BkButton
        text
        theme="primary"
        @click="handleClick">
        {{ dbList.length }}
      </BkButton>
    </EditableBlock>
    <PriviewDbs
      v-model:is-show="isShowSlider"
      v-bind="props"
      @change="handleChange" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { showDatabasesWithPatterns } from '@/services/source/remoteService';

  import PriviewDbs from './PriviewDbs.vue';

  interface Props {
    rowData: {
      clone_db_list: string[];
      cluster: TendbhaModel;
      data_schema_grant: string;
      db_list: string[];
      ignore_db_list: string[];
      target_clusters: TendbhaModel[];
    };
  }

  const props = defineProps<Props>();

  const cloneDbList = defineModel<string[]>('cloneDbList', {
    required: true,
  });

  const ignoreDbList = defineModel<string[]>('ignoreDbList', {
    required: true,
  });

  const dbList = defineModel<string[]>('dbList', {
    required: true,
  });

  const { t } = useI18n();

  const isShowSlider = ref(false);
  let existedDbNameList: string[] = [];

  const rules = [
    {
      message: t('在目标集群已存在 DB： xx，请先修改名称', { n: existedDbNameList.join(',') }),
      trigger: 'blur',
      validator: () => existedDbNameList.length === 0,
    },
  ];

  const { loading, run: fetchData } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess(dataList) {
      const clusterDbsMap: Record<string, boolean> = {};
      dataList.forEach((item) => {
        if (item.cluster_id === props.rowData.cluster.id) {
          dbList.value = item.databases;
        } else {
          const { databases } = item;
          databases.forEach((name) => {
            Object.assign(clusterDbsMap, {
              [name]: true,
            });
          });
        }
      });
      existedDbNameList = dbList.value.filter((name) => clusterDbsMap[name]);
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (rowData?.cluster?.id === 0) {
      return t('请先选择源集群');
    }
    if (rowData?.target_clusters?.length <= 0) {
      return t('请先选择目标集群');
    }
    if (rowData.db_list?.length <= 0) {
      return t('请先选择克隆 DB');
    }
    return '';
  };

  const handleClick = () => {
    isShowSlider.value = true;
  };

  const handleChange = (data: { clone_db_list: string[]; db_list: string[]; ignore_db_list: string[] }) => {
    cloneDbList.value = data.clone_db_list;
    dbList.value = data.db_list;
    ignoreDbList.value = data.ignore_db_list;
  };

  watch(
    () => [
      props.rowData.cluster.id,
      props.rowData.target_clusters,
      props.rowData.clone_db_list,
      props.rowData.ignore_db_list,
    ],
    () => {
      dbList.value = [];
      existedDbNameList = [];
      const clusters = [props.rowData.cluster, ...props.rowData.target_clusters].map((cluster) => cluster.id);
      const validClusterId = clusters.every((id) => Boolean(id));
      if (validClusterId && props.rowData.clone_db_list.length) {
        fetchData({
          infos: clusters.map((id) => ({
            cluster_id: id,
            dbs: props.rowData.clone_db_list,
            ignore_dbs: props.rowData?.ignore_db_list || [],
          })),
        });
      }
    },
  );
</script>
