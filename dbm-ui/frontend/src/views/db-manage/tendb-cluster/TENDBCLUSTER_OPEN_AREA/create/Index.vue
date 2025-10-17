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
  <Teleport
    v-if="templateData"
    to="#dbContentHeaderAppend">
    <span style="font-size: 16px">【{{ templateData.config_name }}】</span>
  </Teleport>
  <SmartAction
    class="tendbcluster-openarea-page"
    :offset-target="getSmartActionOffsetTarget">
    <BkLoading :loading="loading">
      <DbCard
        style="margin-bottom: 24px"
        :title="t('开区目标')">
        <BkForm v-if="templateData">
          <BkFormItem :label="t('模板信息：')">
            <BkButton
              class="template-name"
              text
              theme="primary"
              @click="handleShowTemplateDetail">
              {{ templateData.config_name }}
            </BkButton>
            <span>
              <I18nT
                keypath="(源集群：c，共克隆 n 个 DB)"
                style="font-size: 12px; color: #63656e"
                tag="span">
                <span>{{ templateData.source_cluster.immute_domain }}</span>
                <span style="font-weight: 700">{{ templateData.config_rules.length }}</span>
              </I18nT>
            </span>
          </BkFormItem>
          <BkFormItem
            :label="t('开区目标集群')"
            required>
            <TargetCluster
              ref="targetClusterRef"
              :show-ip-cloumn="templateData.related_authorize.length > 0"
              :variable-list="variableList" />
          </BkFormItem>
        </BkForm>
      </DbCard>
    </BkLoading>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="ml-8 w-88"
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </SmartAction>
  <TemplateDetail
    v-if="templateData"
    v-model:is-show="isShowTemplateDetail"
    :data="templateData" />
  <PreviewData
    v-if="previewData && templateData"
    v-model:is-show="isShowPreivew"
    :data="previewData"
    :source-cluster-id="templateData.source_cluster_id" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getDetail, getPreview } from '@services/source/openarea';

  import { TicketTypes } from '@common/const';

  import PreviewData from './components/preview-data/Index.vue';
  import TargetCluster from './components/target-cluster/Index.vue';
  import TemplateDetail from './components/template-detail/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const targetClusterRef = ref<InstanceType<typeof TargetCluster>>();
  const isShowTemplateDetail = ref(false);
  const isShowPreivew = ref(false);
  const variableList = ref<string[]>([]);

  const { data: templateData, loading } = useRequest(getDetail, {
    defaultParams: [
      {
        id: Number(route.params.id),
      },
    ],
    onSuccess(data) {
      const matchVariableList = data.config_rules.reduce<string[]>((acc, item) => {
        const match = item.target_db_pattern.match(/(?<={)[^{}]+(?=})/g) || [];
        return acc.concat(match);
      }, []);

      variableList.value = _.uniq(matchVariableList);
    },
  });

  const {
    data: previewData,
    loading: isSubmitting,
    run: fetchPreviewData,
  } = useRequest(getPreview, {
    manual: true,
    onSuccess() {
      isShowPreivew.value = true;
    },
  });

  const handleShowTemplateDetail = () => {
    isShowTemplateDetail.value = true;
  };

  const handleSubmit = async () => {
    if (!templateData.value) {
      return;
    }
    const data = await targetClusterRef.value?.getValue();
    if (data?.length) {
      fetchPreviewData({
        config_data: data,
        config_id: templateData.value.id,
      });
    }
  };

  const handleCancel = () => {
    router.push({
      name: TicketTypes.TENDBCLUSTER_OPEN_AREA,
    });
  };

  defineExpose({
    routerBack: handleCancel,
  });
</script>
<style lang="less">
  .tendbcluster-openarea-page {
    .bk-form-label {
      font-size: 12px;
    }

    .template-name {
      font-size: 12px;
      font-weight: 700;
    }
  }
</style>
