<template>
  <BkLoading :loading="isDetailLoading">
    <SmartAction
      class="mysql-openarea-page"
      :offset-target="getSmartActionOffsetTarget">
      <BkForm
        ref="formRef"
        class="mb-32"
        :model="formData">
        <DbCard :title="t('基本信息')">
          <BkFormItem
            :label="t('模块名称')"
            property="config_name"
            required>
            <BkInput
              v-model="formData.config_name"
              :maxlength="32"
              :placeholder="t('请输入模板名称')"
              show-word-limit
              style="width: 560px" />
          </BkFormItem>
        </DbCard>
        <DbCard
          class="mt-18"
          property="source_cluster_id"
          :title="t('模板配置')">
          <BkFormItem
            :label="t('源集群')"
            required>
            <BkButton @click="handleShowClusterSelector">
              <DbIcon
                style="margin-right: 3px"
                type="add" />
              <span>{{ t('选择源集群') }}</span>
            </BkButton>
            <DbOriginalTable
              v-if="targetClusterList.length > 0"
              class="mt-16"
              :columns="colums"
              :data="targetClusterList" />
          </BkFormItem>
          <BkFormItem
            :label="t('克隆的规则')"
            required>
            <ConfigRule
              ref="configRuleRef"
              :cluster-id="formData.source_cluster_id"
              :data="formData.config_rules" />
          </BkFormItem>
        </DbCard>
      </BkForm>
      <ClusterSelector
        v-model:is-show="isShowClusterSelector"
        :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
        only-one-type
        :selected="clusterSelectorValue"
        :tab-list-config="tabListConfig"
        @change="handelClusterChange" />
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmiting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { Form } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { create as createOpenarea, getDetail, update as updateOpenarea } from '@services/openarea';
  import { getTendbhaList } from '@services/source/tendbha';
  import { getTendbsingleList } from '@services/source/tendbsingle';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import { messageSuccess } from '@utils';

  import ConfigRule from './components/config-rule/Index.vue';

  type CreateOpenareaParams = ServiceParameters<typeof createOpenarea>;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const isEditMode = route.name === 'MySQLOpenareaTemplateEdit';

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const genDefaultValue = () => ({
    config_name: '',
    source_cluster_id: 0,
    config_rules: [] as ServiceReturnType<typeof getDetail>['config_rules'],
  });

  const configRuleRef = ref<InstanceType<typeof ConfigRule>>();
  const formRef = ref<InstanceType<typeof Form>>();
  const isSubmiting = ref(false);
  const isShowClusterSelector = ref(false);
  const currentClusterType = ref('tendbha');

  const clusterSelectorValue = shallowRef<Record<string, TendbhaModel[]>>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const targetClusterList = shallowRef<TendbhaModel[]>([]);

  const formData = reactive(genDefaultValue());

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: {
      showPreviewResultTitle: true,
      multiple: false,
    },
    [ClusterTypes.TENDBSINGLE]: {
      showPreviewResultTitle: true,
      multiple: false,
    },
  } as Record<string, TabConfig>;

  const colums = [
    {
      label: t('集群'),
      field: 'master_domain',
    },
    {
      label: t('类型'),
      field: 'cluster_type',
      render: ({ data }: {data: TendbhaModel}) => (data.cluster_type === 'tendbha' ? t('主从') : t('单节点')),
    },
    {
      label: t('状态'),
      render: ({ data }: {data: TendbhaModel}) => (
        <RenderClusterStatus data={data.status} />
      ),
    },
    {
      label: t('操作'),
      width: '100',
      field: 'action',
      render: ({ data }: {data: TendbhaModel}) => (
        <bk-button
          theme="primary"
          text
          onClick={() => handleRemove(data)}>
          { t('删除') }
        </bk-button>
      ),
    },
  ];

  // 编辑态获取模版详情
  const { loading: isDetailLoading, run: fetchTemplateDetail } = useRequest(getDetail, {
    manual: true,
    async onSuccess(data) {
      formData.config_name = data.config_name;
      formData.source_cluster_id = data.source_cluster_id;
      formData.config_rules = data.config_rules;

      if (data.source_cluster.cluster_type === 'tendbha') {
        const listResult = await getTendbhaList({ cluster_ids: [data.source_cluster_id]});
        targetClusterList.value = listResult.results
      } else {
        const listResult = await getTendbsingleList({ cluster_ids: [data.source_cluster_id]});
        targetClusterList.value = listResult.results as TendbhaModel[]
      }
    },
  });

  if (isEditMode) {
    fetchTemplateDetail({
      id: Number(route.params.id),
    });
  }

  const handleRemove = (clusterData: TendbhaModel) => {
    const result = targetClusterList.value.reduce((result, item) => {
      if (item.id !== clusterData.id) {
        result.push(item);
      }
      return result;
    }, [] as TendbhaModel[]);

    targetClusterList.value = result;

    // ClusterSelector 的值回填
    clusterSelectorValue.value = {
      [ClusterTypes.TENDBHA]: _.filter(result, item => item.cluster_type === 'tendbha'),
      [ClusterTypes.TENDBSINGLE]: _.filter(result, item => item.cluster_type === 'tendbsingle'),
    };
  };

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, TendbhaModel[]>) => {
    const selectList = Object.keys(selected).reduce((list: TendbhaModel[], key) => list.concat(...selected[key]), []);
    targetClusterList.value = selectList;
    clusterSelectorValue.value = selected;

    const { id, cluster_type: clusterType } = selectList[0];
    formData.source_cluster_id = id;
    currentClusterType.value = clusterType
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    Promise.all([
      (configRuleRef.value as InstanceType<typeof ConfigRule>).getValue(),
      (formRef.value as InstanceType<typeof Form>).validate(),
    ])
      .then(([configRule]) => {
        const params: CreateOpenareaParams & { id: number } = {
          id: 0,
          bk_biz_id: currentBizId,
          ...formData,
          config_rules: configRule,
          cluster_type: currentClusterType.value,
        };
        if (isEditMode) {
          params.id = Number(route.params.id);
        }
        const handler = isEditMode ? updateOpenarea : createOpenarea;
        return handler(params).then(() => {
          messageSuccess(isEditMode ? t('编辑成功') : t('新建成功'));
          window.changeConfirm = false;
          router.push({
            name: 'MySQLOpenareaTemplate',
          });
        });
      })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleReset = () => {
    Object.assign(formData, genDefaultValue());
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MySQLOpenareaTemplate',
      });
    },
  });
</script>
