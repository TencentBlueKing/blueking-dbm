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
  <div class="config-detail-page">
    <div class="config-detail-page-content db-scroll-y">
      <!-- 参数信息 -->
      <DbCard>
        <BkAlert
          class="mb-16"
          closable
          theme="info"
          :title="t('业务配置参数说明')" />
        <ParamTable
          ref="paramTableRef"
          :cluster-type="clusterType"
          :conf-type="confType"
          :config-name="configName"
          :level-info="levelParams.level_info"
          :level-name="levelParams.level_name"
          :level-value="levelParams.level_value"
          selectable
          :version="version"
          @change="handleParamChange">
        </ParamTable>
      </DbCard>
    </div>
  </div>
  <Teleport to="#dbContentTitleAppend">
    <div class="config-detail-header">
      <span class="config-detail-nav-title">
        {{ configTypeName }}
      </span>
      <span class="config-detail-meta">
        <span v-if="detailData.name">{{ t('配置名称') }}：{{ detailData.name }}</span>
        <span v-if="detailData.updated_by || detailData.updated_at">
          {{ t('最近更新') }}：{{ detailData.updated_by || '--' }} / {{ detailData.updated_at || '--' }}
        </span>
        <span v-if="detailData.description">{{ t('描述') }}：{{ detailData.description }}</span>
      </span>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getLevelConfig, getListConfTypes } from '@services/source/configs';

  import ParamTable from '@views/db-configure-new/components/ParamTable.vue';
  import { useLevelParams } from '@views/db-configure-new/hooks/useLevelParams';

  interface Props {
    clusterType: string;
    confType: string;
    version: string;
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const paramTableRef = ref<InstanceType<typeof ParamTable>>();

  const configName = computed(() => detailData.value.name || '');
  const configTypeName = ref('');

  // 获取 confType 对应的显示名称
  useRequest(getListConfTypes, {
    defaultParams: [{ meta_cluster_type: props.clusterType }],
    onSuccess(res) {
      const matched = res.find((item) => item.conf_type === props.confType);
      configTypeName.value = matched?.name || props.confType;
    },
  });

  type LevelConfigResult = ServiceReturnType<typeof getLevelConfig>;

  const detailData = ref<Partial<LevelConfigResult>>({});

  // 层级参数
  const levelParams = useLevelParams(false);

  const fetchParams = computed(() => ({
    conf_type: props.confType,
    meta_cluster_type: props.clusterType,
    version: props.version,
    ...levelParams.value,
  }));

  /** 获取配置详情 */
  const { run: fetchDetail } = useRequest(getLevelConfig, {
    defaultParams: [fetchParams.value, { permission: 'page' }],
    onSuccess(res) {
      detailData.value = res;
    },
  });

  /** 参数变化回调 */
  const handleParamChange = () => {
    fetchDetail(fetchParams.value, { permission: 'page' });
  };

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.push({
          name: 'DbConfigureList',
          params: {
            clusterType: props.clusterType,
          },
        });
        return;
      }
      router.push({
        name: route.query.from as string,
        params: {
          clusterType: props.clusterType,
          confType: route.params.confType as string,
          parentId: route.params.parentId as string,
          treeId: route.params.treeId as string,
        },
      });
    },
  });
</script>

<style lang="less" scoped>
  .config-detail-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .config-detail-nav-title {
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 16px;
    line-height: 24px;
  }

  .config-detail-meta {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #979ba5;

    &::before {
      content: '';
      display: inline-block;
      width: 1px;
      height: 14px;
      background: #dcdee5;
    }
  }

  .config-detail-page-content {
    padding: 24px;
    border-radius: 2px;

    :deep(.db-card-content) {
      padding-top: 0;
    }
  }
</style>
