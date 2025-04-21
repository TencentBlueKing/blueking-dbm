<template>
  <BkSelect
    v-model="modelValue"
    :disabled="disabled"
    multiple
    multiple-mode="tag"
    :remote-method="handleSearch"
    :scroll-loading="listTagLoading"
    @scroll-end="loadMore">
    <BkOption
      v-for="item in tagList"
      :key="item.id"
      :label="item.value"
      :value="item.id" />
    <template #extension>
      <BkForm
        v-if="isEdit"
        ref="formRef"
        class="edit-form"
        :model="formData"
        :rules="rules">
        <div class="editor-wrapper">
          <BkFormItem
            error-display-type="tooltips"
            label=""
            property="tag"
            required>
            <BkInput
              v-model="formData.tag"
              :readonly="inputLoading" />
          </BkFormItem>
          <BkButton
            :loading="inputLoading"
            text
            @click="handleCreate">
            <DbIcon
              class="check-line-button"
              type="check-line" />
          </BkButton>
          <BkButton
            :disabled="inputLoading"
            text
            @click="handleClose">
            <DbIcon
              class="close-button"
              type="close" />
          </BkButton>
        </div>
      </BkForm>
      <div
        v-else
        class="operation-wrapper">
        <div
          class="create-tag"
          @click.stop="handleEdit">
          <DbIcon
            class="icon"
            type="plus-circle" />
          <span class="ml-2">{{ t('新建标签') }}</span>
        </div>
        <BkDivider
          direction="vertical"
          type="solid" />
        <div
          class="link-to-manage"
          @click.stop="handleLink">
          <DbIcon
            class="icon"
            type="link" />
          <span class="ml-2">{{ t('跳转管理页') }}</span>
        </div>
      </div>
    </template>
  </BkSelect>
</template>

<script setup lang="tsx">
  import { uniqBy } from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { createTag, listTag, validateTag } from '@services/source/tag';

  import { messageSuccess } from '@utils';

  interface Props {
    bkBizId: number;
    defaultList?: DbResourceModel['labels'];
    disabled?: boolean;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<number[]>({
    default: () => [],
  });

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const formRef = useTemplateRef('formRef');

  const isEdit = ref(false);
  const searchVal = ref('');
  const validateLoading = ref(false);

  const tagList = shallowRef<ServiceReturnType<typeof listTag>['results']>([]);

  const formData = reactive({
    tag: '',
  });

  const pagination = reactive({
    count: 0,
    limit: 10,
    offset: 0,
  });

  const rules = {
    tag: [
      {
        message: t('不能为空'),
        required: true,
        trigger: 'blur',
      },
      {
        trigger: 'blur',
        validator: (value: string) => {
          validateLoading.value = true;
          return validateTag({
            bk_biz_id: props.bkBizId,
            tags: [{ key: 'dbresource', value }],
          })
            .then((existData) => {
              return existData.length > 0 ? t('标签已存在') : true;
            })
            .finally(() => {
              validateLoading.value = false;
            });
        },
      },
    ],
  };

  const isBusiness = route.name === 'BizResourcePool';

  const inputLoading = computed(() => createLoading.value || validateLoading.value);

  const { loading: listTagLoading, run: runListTag } = useRequest(listTag, {
    manual: true,
    onSuccess(data) {
      pagination.count = data.count;
      tagList.value = uniqBy([...tagList.value, ...data.results], 'value');
    },
  });

  const { loading: createLoading, run: runCreate } = useRequest(createTag, {
    manual: true,
    async onSuccess() {
      const data = await listTag({
        bk_biz_id: props.bkBizId,
        limit: 1,
        offset: pagination.count,
        ordering: 'create_at',
        type: 'resource',
      });
      tagList.value = uniqBy([...tagList.value, ...data.results], 'value');
      pagination.count = data.count;
      modelValue.value = [...modelValue.value, data.results[0].id];
      handleClose();
      messageSuccess(t('新建成功'));
    },
  });

  watch(
    () => props.bkBizId,
    () => {
      modelValue.value = [];
      tagList.value = [];
      runListTag({
        bk_biz_id: props.bkBizId,
        ordering: 'create_at',
        type: 'resource',
      });
    },
  );

  watch(searchVal, () => {
    pagination.offset = 0;
    pagination.count = 0;
    initTagList();
    runListTag({
      bk_biz_id: props.bkBizId,
      limit: pagination.limit,
      offset: pagination.offset,
      ordering: 'create_at',
      type: 'resource',
      value: searchVal.value,
    });
  });

  const loadMore = () => {
    if (listTagLoading.value || pagination.offset >= pagination.count) {
      return;
    }
    pagination.offset = Math.min(pagination.count, pagination.offset + pagination.limit);
    runListTag({
      bk_biz_id: props.bkBizId,
      limit: pagination.limit,
      offset: pagination.offset,
      type: 'resource',
      value: searchVal.value,
    });
  };

  const handleEdit = () => {
    isEdit.value = true;
  };

  const handleClose = () => {
    formData.tag = '';
    isEdit.value = false;
  };

  const handleCreate = () => {
    formRef.value!.validate().then(() => {
      runCreate({
        bk_biz_id: props.bkBizId,
        tags: [
          {
            key: 'dbresource',
            value: formData.tag,
          },
        ],
        type: 'resource',
      });
    });
  };

  const handleLink = () => {
    const route = router.resolve({
      name: isBusiness ? 'BizResourceTag' : 'resourceTagsManagement',
    });
    window.open(route.href);
  };

  const handleSearch = (val: string) => {
    searchVal.value = val;
  };

  const initTagList = () => {
    if (props.defaultList?.length) {
      tagList.value = props.defaultList.map((item) => ({
        id: item.id,
        value: item.name,
      })) as ServiceReturnType<typeof listTag>['results'];
    } else {
      tagList.value = [];
    }
  };

  onMounted(() => {
    initTagList();
    runListTag({
      bk_biz_id: props.bkBizId,
      limit: pagination.limit,
      offset: 0,
      ordering: 'create_time',
      type: 'resource',
    });
  });
</script>

<style scoped lang="less">
  .operation-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-around;
    width: 100%;

    .icon {
      width: 14px;
      height: 14px;
      color: #979ba5;
    }

    .create-tag {
      cursor: pointer;
    }

    .link-to-manage {
      cursor: pointer;
    }
  }

  .edit-form {
    width: 100%;

    .editor-wrapper {
      display: flex;
      align-items: center;
      width: 100%;
      padding: 8px;

      :deep(.bk-form-item) {
        margin: 0;
        flex: 1;
      }

      .check-line-button {
        margin-right: 12.5px;
        margin-left: 12.5px;
        font-size: 14px;
        color: #2dcb56;
        cursor: pointer;
      }

      .close-button {
        font-size: 18px;
        color: #979ba5;
        cursor: pointer;
      }
    }
  }
</style>
