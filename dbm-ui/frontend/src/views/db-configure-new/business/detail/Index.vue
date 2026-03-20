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
      <!-- 基础信息 -->
      <DbCard
        mode="collapse"
        :title="t('基础信息')">
        <BkLoading :loading="loading">
          <BkForm class="base-info-form">
            <div class="base-info-form-row">
              <BkFormItem :label="t('配置名称')">
                {{ detailData.name || '--' }}
              </BkFormItem>
              <BkFormItem :label="t('配置文件')">
                {{ detailData.version || '--' }}
              </BkFormItem>
            </div>
            <div class="base-info-form-row">
              <BkFormItem :label="t('最近更新人')">
                {{ detailData.updated_by || '--' }}
              </BkFormItem>
              <BkFormItem :label="t('更新时间')">
                {{ detailData.updated_at || '--' }}
              </BkFormItem>
            </div>
            <div class="base-info-form-row">
              <BkFormItem :label="t('描述')">
                {{ detailData.description || '--' }}
              </BkFormItem>
            </div>
          </BkForm>
        </BkLoading>
      </DbCard>

      <!-- 参数信息 -->
      <DbCard
        class="mt-16"
        mode="collapse"
        :title="t('参数信息')">
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
    <span class="config-detail-nav-title">
      {{ configTypeName }}
    </span>
    <span class="config-detail-nav-desc">
      {{ configName }}
    </span>
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
  const { loading, run: fetchDetail } = useRequest(getLevelConfig, {
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
  .config-detail-nav-title {
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 16px;
    line-height: 24px;
  }

  .config-detail-nav-desc {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;
  }

  .config-detail-nav-desc::before {
    position: absolute;
    top: 50%;
    left: 0;
    width: 1px;
    height: 16px;
    content: '';
    background: #dcdee5;
    transform: translateY(-50%);
  }

  .config-detail-page-content {
    height: calc(100vh - var(--notice-height) - 100px);
    padding: 24px;
  }

  .base-info-form {
    display: flex;
    flex-direction: column;
    align-self: stretch;
    padding: 16px 24px;
    background: #fff;
    border-radius: 2px;
  }

  .base-info-form-row {
    display: flex;
    width: 100%;

    :deep(.bk-form-item) {
      flex: 1;
      margin-bottom: 0;
    }
  }
</style>
