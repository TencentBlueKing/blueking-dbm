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
      <div
        v-if="isEdit"
        class="editor-wrapper">
        <BkInput
          v-model="tagValue"
          class="editor"
          @blur="handleClose" />
        <div
          class="operator-wrapper"
          @click="handleCreate">
          <DbIcon
            class="check-line"
            type="check-line" />
        </div>
        <div
          class="operator-wrapper"
          @click="handleClose">
          <DbIcon
            class="close"
            type="close" />
        </div>
      </div>
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

  import type DbResourceModel from '@services/model/db-resource/DbResource';
  import { createTag, listTag } from '@services/source/tag';

  import { messageSuccess } from '@utils';

  interface Props {
    bkBizId: number;
    disabled?: boolean;
    defaultList?: DbResourceModel['labels'];
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<number[]>({
    default: () => [],
  });

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const isEdit = ref(false);
  const tagValue = ref('');
  const searchVal = ref('');
  const tagList = ref<ServiceReturnType<typeof listTag>['results']>([]);
  const pagination = reactive({
    offset: 0,
    limit: 10,
    count: 0,
  });

  const isBusiness = route.name === 'BizResourcePool';

  const { run: runListTag, loading: listTagLoading } = useRequest(listTag, {
    manual: true,
    onSuccess(data) {
      pagination.count = data.count;
      tagList.value = uniqBy([...tagList.value, ...data.results], 'value');
    },
  });

  const { run: runCreate } = useRequest(createTag, {
    manual: true,
    onSuccess() {
      pagination.count += 1;
      loadMore();
      isEdit.value = false;
      messageSuccess(t('新建成功'));
    },
  });

  const loadMore = () => {
    if (listTagLoading.value) {
      return;
    }
    if (tagList.value.length >= pagination.count) {
      return;
    }
    pagination.offset = Math.min(pagination.count, pagination.offset + pagination.limit);
    runListTag({
      bk_biz_id: props.bkBizId,
      offset: pagination.offset,
      limit: pagination.limit,
      value: searchVal.value,
    });
  };

  watch(
    () => props.bkBizId,
    () => {
      modelValue.value = [];
      tagList.value = [];
      runListTag({
        bk_biz_id: props.bkBizId,
      });
    },
  );

  watch(searchVal, () => {
    pagination.offset = 0;
    pagination.count = 0;
    initTagList();
    runListTag({
      bk_biz_id: props.bkBizId,
      offset: pagination.offset,
      limit: pagination.limit,
      value: searchVal.value,
    });
  });

  const handleEdit = () => {
    isEdit.value = true;
  };

  const handleClose = () => {
    isEdit.value = false;
  };

  const handleCreate = () => {
    runCreate({
      bk_biz_id: props.bkBizId,
      tags: [
        {
          key: 'dbresource',
          value: tagValue.value,
        },
      ],
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
      offset: 0,
      limit: pagination.limit,
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

  .editor-wrapper {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 8px;

    .editor {
      flex: 1;
    }

    .operator-wrapper {
      display: flex;
      width: 32px;
      height: 32px;
      align-items: center;
      border-radius: 16px;
      justify-content: center;

      &:hover {
        cursor: pointer;
        background-color: #e1ecff;
      }

      .check-line {
        width: 13px;
        height: 9.31px;
        margin-right: 12.5px;
        margin-left: 12.5px;
        color: #2dcb56;
        cursor: pointer;
      }

      .close {
        width: 10px;
        height: 10px;
        color: #979ba5;
        cursor: pointer;
      }
    }
  }
</style>
