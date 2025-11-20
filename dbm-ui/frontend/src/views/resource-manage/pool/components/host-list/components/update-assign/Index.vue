<template>
  <BkDialog
    class="update-assign-dialog"
    :is-show="isShow"
    render-directive="if"
    width="600"
    @closed="handleCancel">
    <template #header>
      <div class="update-assign-header">
        <div>{{ t('编辑资源归属') }}</div>
        <div class="update-assign-sub-title">
          {{ editData?.ip || '' }}
        </div>
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
        <DbAppSelect
          :disabled="isBusiness"
          :list="globalBizsStore.bizs"
          :model-value="currentApp"
          :show-public-biz="!isBusiness"
          @change="handleAppChange" />
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
        v-if="formData.for_biz !== 0"
        :label="t('资源标签')"
        property="labels">
        <TagSelector
          v-model="formData.labels"
          :bk-biz-id="formData.for_biz"
          :default-list="editData.labels"
          :disabled="!formData.for_biz && formData.for_biz !== 0" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        :loading="isUpdating"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { getBizs } from '@services/source/cmdb';
  import { updateResource } from '@services/source/dbresourceResource';
  import { fetchDbTypeList } from '@services/source/infras';
  import type { BizItem } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import DbAppSelect from '@components/db-app-select/Index.vue';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    editData: DbResourceModel;
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const formRef = useTemplateRef('formRef');
  const globalBizsStore = useGlobalBizs();
  const route = useRoute();

  const formData = reactive({
    for_biz: globalBizsStore.currentBizId,
    labels: [] as DbResourceModel['labels'][number]['id'][],
    resource_type: '',
  });
  const bizList = shallowRef<ServiceReturnType<typeof getBizs>>([]);
  const dbTypeList = shallowRef<ServiceReturnType<typeof fetchDbTypeList>>([]);

  const isBusiness = route.name === 'BizResourcePool';
  const currentApp = shallowRef<BizItem | undefined>();

  watch(
    () => props.editData,
    () => {
      if (!Object.keys(props.editData).length) {
        return;
      }
      currentApp.value = globalBizsStore.bizIdMap.get(props.editData.for_biz.bk_biz_id);
      formData.for_biz = props.editData.for_biz.bk_biz_id;
      formData.resource_type = props.editData.resource_type;
      formData.labels = props.editData.labels.map((item) => item.id);
    },
    {
      deep: true,
      immediate: true,
    },
  );

  useRequest(getBizs, {
    onSuccess(data) {
      bizList.value = [
        {
          bk_biz_id: 0,
          display_name: t('公共资源池'),
        } as BizItem,
        ...data,
      ];
    },
  });

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

  const { loading: isUpdating, run: runUpdate } = useRequest(updateResource, {
    manual: true,
    onSuccess() {
      emits('refresh');
      isShow.value = false;
    },
  });

  const handleAppChange = (appInfo?: IAppItem) => {
    currentApp.value = appInfo;
    formData.for_biz = appInfo!.bk_biz_id;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    runUpdate({
      bk_host_ids: [props.editData.bk_host_id],
      for_biz: Number(formData.for_biz),
      labels: formData.labels,
      rack_id: '',
      resource_type: formData.resource_type,
      storage_device: {},
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .update-assign-dialog {
    .update-assign-header {
      display: flex;
      align-items: center;
    }

    .update-assign-sub-title {
      position: relative;
      display: flex;
      height: 22px;
      padding-left: 8px;
      margin-left: 8px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 14px;
      line-height: 22px;
      letter-spacing: 0;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 6px;
        left: 0;
        width: 1px;
        height: 14px;
        background-color: #979ba580;
        content: '';
      }
    }
  }
</style>
