<template>
  <BkPopover
    :is-show="isShowUpdateAlias"
    placement="top"
    theme="light"
    trigger="manual"
    @after-hidden="handlePopoverhide"
    @after-show="handlePopoverShown">
    <div
      class="cluster-alias-edit-btn"
      :class="{
        'is-active': isActive,
      }">
      <AuthButton
        :action-id="actionId"
        :permission="checkEditPermission(data)"
        :resource="data.id"
        text
        theme="primary"
        @click="handleShowEdit">
        <DbIcon type="edit" />
      </AuthButton>
    </div>
    <template #content>
      <div style="margin-bottom: 8px; font-size: 16px; font-weight: bold">
        {{ t('编辑集群别名') }}
      </div>
      <BkForm
        ref="bkform"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('集群别名')"
          property="new_alias"
          required>
          <BkInput
            v-model="formData.new_alias"
            style="width: 300px; margin-top: 8px" />
          <div style="display: flex; margin-top: 8px"></div>
        </BkFormItem>
      </BkForm>
      <div style="display: flex">
        <BkButton
          :loading="isUpdateing"
          size="small"
          style="margin-left: auto"
          theme="primary"
          @click="handleEditAlias">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          size="small"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateClusterAlias } from '@services/source/dbbase';

  interface Props {
    data: {
      cluster_alias: string;
      cluster_name: string;
      db_type: string;
      id: number;
      permission: Record<string, boolean>;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<(e: 'success') => void>();

  const { t } = useI18n();
  const fromRef = useTemplateRef('bkform');

  const isActive = ref(false);

  const { loading: isUpdateing, run: runUpdateClusterAlias } = useRequest(updateClusterAlias, {
    manual: true,
    onSuccess() {
      isShowUpdateAlias.value = false;
      emits('success');
    },
  });

  const formData = reactive({
    new_alias: props.data.cluster_alias,
  });
  const isShowUpdateAlias = ref(false);

  const actionId = computed(() => `${props.data.db_type}_edit`);

  const checkEditPermission = (data: Props['data']) => {
    const permissionKey = `${props.data.db_type}_edit` as keyof typeof data.permission;
    return data.permission[permissionKey];
  };

  const handlePopoverShown = () => {
    formData.new_alias = props.data.cluster_alias;
    isActive.value = true;
  };
  const handlePopoverhide = () => {
    isActive.value = false;
  };
  const handleShowEdit = () => {
    isShowUpdateAlias.value = true;
  };

  const handleEditAlias = () => {
    fromRef.value!.validate().then(() => {
      runUpdateClusterAlias({
        cluster_id: props.data.id,
        ...formData,
      });
    });
  };

  const handleCancel = () => {
    isShowUpdateAlias.value = false;
  };
</script>
<style lang="less">
  tr.vxe-body--row {
    &:hover {
      .cluster-alias-edit-btn {
        display: block;
      }
    }
  }

  .cluster-alias-edit-btn {
    display: none;
    padding-left: 4px;
    color: #3a84ff;
    cursor: pointer;

    &.is-active {
      display: block;

      * {
        display: block !important;
      }
    }
  }
</style>
