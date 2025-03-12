<template>
  <BkDialog
    :is-show="isShow"
    render-directive="if"
    :title="t('编辑资源归属')"
    width="600">
    <template #header>
      <div class="header-wrapper">
        <span class="title">{{ t('导入资源池') }}</span>
        <span class="title-divider">|</span>
        <span class="biz-name">
          {{ data.ip }}
        </span>
      </div>
    </template>
    <BkForm
      ref="formRef"
      class="mt-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('所属业务')"
        property="for_biz"
        required>
        <BkSelect
          v-model="formData.for_biz"
          :allow-empty-values="[0]">
          <BkOption
            v-for="bizItem in bizList"
            :key="bizItem.bk_biz_id"
            :label="bizItem.display_name"
            :value="bizItem.bk_biz_id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('所属DB')"
        property="resource_type"
        required>
        <BkSelect v-model="formData.resource_type">
          <BkOption
            v-for="item in dbTypeList"
            :key="item.id"
            :label="item.name"
            :value="item.id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('资源标签')"
        property="labels">
        <TagSelector
          v-model="formData.labels"
          :bk-biz-id="formData.for_biz"
          :disabled="!formData.for_biz && formData.for_biz !== 0" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <div>
        <BkButton
          v-bk-tooltips="tooltip"
          :loading="isImporting"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { importResource } from '@services/source/dbresourceResource';
  import { fetchDbTypeList } from '@services/source/infras';
  import type { BizItem } from '@services/types';

  import { useGlobalBizs, useSystemEnviron } from '@stores';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  import { useImportResourcePoolTooltip } from '../../hooks/useImportResourcePoolTip';

  interface Props {
    data: FaultOrRecycleMachineModel;
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const systemEnvironStore = useSystemEnviron();
  const { successMessage, tooltip } = useImportResourcePoolTooltip();

  const formRef = useTemplateRef('formRef');

  const formData = reactive({
    for_biz: 0,
    labels: [] as DbResourceModel['labels'][number]['id'][],
    resource_type: '',
  });
  const dbTypeList = shallowRef<ServiceReturnType<typeof fetchDbTypeList>>([]);

  const bizList = computed(() => [
    {
      bk_biz_id: 0,
      display_name: t('公共资源池'),
    } as BizItem,
    ...globalBizsStore.bizs,
  ]);

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      dbTypeList.value = [
        {
          id: 'PUBLIC',
          name: t('通用'),
        },
        ...data,
      ];
    },
  });

  const { loading: isImporting, run: runImport } = useRequest(importResource, {
    manual: true,
    onSuccess({ task_ids: taskIds }) {
      emits('refresh');
      isShow.value = false;
      successMessage(taskIds);
    },
  });

  const handleSubmit = async () => {
    await formRef.value!.validate();
    runImport({
      bk_biz_id: systemEnvironStore.urls.DBA_APP_BK_BIZ_ID,
      for_biz: Number(formData.for_biz),
      hosts: [
        {
          bk_cloud_id: props.data.bk_cloud_id,
          host_id: props.data.bk_host_id,
          ip: props.data.ip,
        },
      ],
      labels: formData.labels,
      resource_type: formData.resource_type,
      return_resource: true,
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .header-wrapper {
    display: flex;
    align-items: center;
    font-size: 14px;
    color: #979ba5;

    .title {
      font-size: 20px;
      color: #313238;
    }

    .title-divider {
      margin: 0 8px 0 11px;
    }
  }
</style>
