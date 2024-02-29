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
    v-bkloading="{loading: loading}"
    class="config-info">
    <DbOriginalTable
      :columns="columns"
      :data="data.conf_items"
      height="100%"
      :show-overflow-tooltip="false" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getLevelConfig } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  interface Props {
    queryInfos: {
      dbModuleId: number,
      version: string,
      clusterId: number
    }
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const data = shallowRef<ServiceReturnType<typeof getLevelConfig>>({
    name: '',
    version: '',
    description: '',
    conf_items: [],
  });

  const columns = [
    {
      label: t('参数项'),
      field: 'conf_name',
    },
    {
      label: t('参数值'),
      field: 'conf_value',
    },
    {
      label: t('描述'),
      field: 'description',
    },
    {
      label: t('重启实例生效'),
      field: 'need_restart',
      width: 200,
      render: ({ cell }: { cell: number }) => (cell === 1 ? t('是') : t('否')),
    },
  ];

  const {
    loading,
    run: getLevelConfigRun,
  } = useRequest(getLevelConfig, {
    manual: true,
  });

  watch(() => props.queryInfos, (infos) => {
    const {
      dbModuleId,
      version,
      clusterId,
    } = infos;
    if (dbModuleId && version && clusterId) {
      getLevelConfigRun({
        bk_biz_id: currentBizId,
        level_value: props.queryInfos.clusterId,
        meta_cluster_type: ClusterTypes.SQLSERVER_HA,
        level_name: 'cluster',
        conf_type: 'dbconf',
        version: props.queryInfos.version,
        level_info: {
          module: String(props.queryInfos.dbModuleId),
        },
      });
    }
  }, {
    immediate: true,
    deep: true,
  });
</script>

  <style lang="less" scoped>
  .config-info {
    height: calc(100% - 96px);
    margin: 24px 0;
  }
</style>
