<template>
  <Teleport
    v-if="openareaTemplateData"
    to="#dbContentHeaderAppend">
    <span style="font-size: 16px">【{{ openareaTemplateData.config_name }}】</span>
  </Teleport>
  <SmartAction
    class="mysql-openarea-page"
    :offset-target="getSmartActionOffsetTarget">
    <BkLoading :loading="isLoading">
      <DbCard
        style="margin-bottom: 24px"
        :title="t('开区目标')">
        <BkForm v-if="openareaTemplateData">
          <BkFormItem :label="t('模板信息：')">
            <BkButton
              class="template-name"
              text
              theme="primary"
              @click="handleShowTemplateDetail">
              {{ openareaTemplateData.config_name }}
            </BkButton>
            <span>
              <I18nT
                keypath="(源集群：c，共克隆 n 个 DB)"
                style="font-size: 12px; color: #63656e"
                tag="span">
                <span>{{ openareaTemplateData.source_cluster.immute_domain }}</span>
                <span style="font-weight: 700">{{ openareaTemplateData.config_rules.length }}</span>
              </I18nT>
            </span>
          </BkFormItem>
          <BkFormItem
            :label="t('开区目标集群')"
            required>
            <TargetCluster
              ref="targetClusterRef"
              :cluster-type="clusterType"
              :show-ip-cloumn="openareaTemplateData.related_authorize.length > 0"
              :variable-list="variableList" />
          </BkFormItem>
        </BkForm>
      </DbCard>
    </BkLoading>
    <template #action>
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="ml-8 w-88"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
    <BkSideslider
      v-model:is-show="isShowTemplateDetail"
      :title="t('模板详情【templateName配置 】', { name: openareaTemplateData?.config_name })"
      :width="1100">
      <TemplateDetail
        v-if="openareaTemplateData"
        :data="openareaTemplateData" />
    </BkSideslider>
    <BkDialog
      v-model:is-show="isShowPreivew"
      :disabled-confirm="isExistedErrorMsg"
      :height="760"
      :title="t('请确认以下开区内容：')"
      :width="1536">
      <PreviewData
        v-if="previewData && openareaTemplateData"
        ref="previewDataRef"
        :data="previewData"
        :source-cluster-id="openareaTemplateData.source_cluster_id" />
      <template #footer>
        <BkButton
          class="mr-2"
          :loading="confirmSubmitLoading"
          theme="primary"
          @click="handleConfirmSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          :disabled="confirmSubmitLoading"
          @click="handleClosePreview">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </SmartAction>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import { getDetail, getPreview } from '@services/source/openarea';

  import { ClusterTypes } from '@common/const';

  import PreviewData from './components/PreviewData.vue';
  import TargetCluster from './components/target-cluster/Index.vue';
  import TemplateDetail from './components/template-detail/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const targetClusterRef = ref<InstanceType<typeof TargetCluster>>();
  const isSubmiting = ref(false);
  const isShowTemplateDetail = ref(false);
  const isShowPreivew = ref(false);
  const variableList = ref<string[]>([]);
  const clusterType = ref(ClusterTypes.TENDBHA);
  const previewDataRef = ref<InstanceType<typeof PreviewData>>();
  const confirmSubmitLoading = ref(false);

  const previewData = shallowRef<ServiceReturnType<typeof getPreview>>();

  const isExistedErrorMsg = computed(() =>
    previewData.value?.config_data.some((item) => item.execute_objects.some((obj) => obj.error_msg)),
  );

  const { loading: isLoading, data: openareaTemplateData } = useRequest(getDetail, {
    defaultParams: [
      {
        id: Number(route.params.id),
      },
    ],
    onSuccess(data) {
      const matchVariableList = data.config_rules.reduce((result, item) => {
        const match = item.target_db_pattern.match(/(?<={)[^{}]+(?=})/g) || [];
        return result.concat(match);
      }, [] as string[]);

      variableList.value = _.uniq(matchVariableList);
      clusterType.value = data.cluster_type as ClusterTypes;
    },
  });

  const handleShowTemplateDetail = () => {
    isShowTemplateDetail.value = true;
  };

  const handleSubmit = () => {
    if (!openareaTemplateData.value) {
      return;
    }
    isSubmiting.value = true;
    (targetClusterRef.value as InstanceType<typeof TargetCluster>)
      .getValue()
      .then((data) =>
        getPreview({
          config_id: (openareaTemplateData.value as OpenareaTemplateModel).id,
          config_data: data as any,
        }).then((data) => {
          isShowPreivew.value = true;
          previewData.value = data;
        }),
      )
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleCancel = () => {
    router.push({
      name: 'MySQLOpenareaTemplate',
    });
  };

  const handleConfirmSubmit = () => {
    previewDataRef.value!.submit().finally(() => (confirmSubmitLoading.value = false));
  };

  const handleClosePreview = () => {
    isShowPreivew.value = false;
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MySQLOpenareaTemplate',
      });
    },
  });
</script>
<style lang="less">
  .mysql-openarea-page {
    .bk-form-label {
      font-size: 12px;
    }

    .template-name {
      font-size: 12px;
      font-weight: 700;
    }
  }
</style>
