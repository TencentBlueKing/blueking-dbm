<template>
  <BkSelect
    v-model="modelValue"
    :disabled="disabled"
    multiple
    multiple-mode="tag">
    <BkOption
      v-for="item in tagList"
      :key="item.id"
      :label="item.name"
      :value="item.id" />
    <template #extension>
      <div
        v-if="isEdit"
        class="editor-wrapper">
        <BkInput
          v-model="tagValue"
          class="editor"
          @blur="handleClose" />
        <DbIcon
          class="check-line"
          type="check-line"
          @click="handleCreate" />
        <DbIcon
          class="close"
          type="close"
          @click="handleClose" />
      </div>
      <div
        v-else
        class="operation-wrapper">
        <div
          class="create-tag"
          @click="handleEdit">
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
          @click="handleLink">
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
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createTag, listTag } from '@services/source/tag';

  import { messageSuccess } from '@utils';

  interface Props {
    bkBizId: number;
    disabled?: boolean;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string[]>({
    default: [],
  });

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const isEdit = ref(false);
  const tagValue = ref('');
  const tagList = ref<
    Array<{
      id: number;
      name: string;
    }>
  >([]);

  const isBusiness = route.name === 'BizResourcePool';

  const { run: runListTag } = useRequest(listTag, {
    onSuccess(data) {
      tagList.value = data.results.map((item) => ({
        id: item.id,
        name: item.value,
      }));
    },
    manual: true,
  });

  const { run: runCreate } = useRequest(createTag, {
    manual: true,
    onSuccess() {
      runListTag({ bk_biz_id: props.bkBizId });
      isEdit.value = false;
      messageSuccess(t('新建成功'));
    },
  });

  watch(
    () => props.bkBizId,
    () => {
      modelValue.value = [];
      runListTag({ bk_biz_id: props.bkBizId });
    },
    {
      immediate: true,
    },
  );

  const handleEdit = () => {
    isEdit.value = true;
  };

  const handleClose = () => {
    isEdit.value = false;
  };

  const handleCreate = () => {
    console.log(213123123);
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
    .check-line {
      width: 13px;
      height: 9.31px;
      color: #2dcb56;
      margin-left: 8px;
      margin-right: 12.5px;
      cursor: pointer;
    }
    .close {
      width: 10px;
      height: 10px;
      color: #979ba5;
      cursor: pointer;
    }
  }
</style>
