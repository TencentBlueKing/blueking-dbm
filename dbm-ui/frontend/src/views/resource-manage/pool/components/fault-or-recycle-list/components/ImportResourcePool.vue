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

  import { useGlobalBizs } from '@stores';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  import { messageSuccess } from '@utils';

  interface Props {
    data: FaultOrRecycleMachineModel;
  }

  interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();

  const formRef = useTemplateRef('formRef');

  const formData = reactive({
    for_biz: 0,
    resource_type: '',
    labels: [] as DbResourceModel['labels'][number]['id'][],
  });
  const dbTypeList = shallowRef<ServiceReturnType<typeof fetchDbTypeList>>([]);

  const bizList = computed(() => (
    [
      {
        bk_biz_id: 0,
        display_name: t('公共资源池'),
      } as BizItem,
      ...globalBizsStore.bizs
    ]
  ));

  const path = router.resolve({
    name: 'taskHistory'
  });

  const tooltip = {
    theme: 'light',
    content: () => (
      <div>
        {t('提交后，将会进行主机初始化任务，具体的导入结果，可以通过“')}
        <a href={path.href} target='_blank'>
          {t('任务历史')}
        </a>
        {t('”查看')}
      </div>
    )
  };

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
    onSuccess() {
      emits('refresh');
      isShow.value = false;
      messageSuccess(t('操作成功'));
    },
  });

  const handleSubmit = async () => {
    await formRef.value!.validate();
    runImport({
      hosts: [
        {
          ip: props.data.ip,
          host_id: props.data.bk_host_id,
          bk_cloud_id: props.data.bk_cloud_id,
        },
      ],
      for_biz: Number(formData.for_biz),
      resource_type: formData.resource_type,
      labels: formData.labels,
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
