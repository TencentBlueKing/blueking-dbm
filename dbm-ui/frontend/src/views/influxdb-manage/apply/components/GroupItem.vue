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
  <BkFormItem
    :label="$t('分组名')"
    property="details.group_id"
    required>
    <BkSelect
      class="item-input"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading"
      :model-value="localGroupId"
      @change="handleChangeId"
      @toggle="handleToggleSelector">
      <BkOption
        v-for="item in groupList"
        :key="item.id"
        :label="item.name"
        :value="item.id" />
      <template #extension>
        <div style="flex: 1; text-align: center;">
          <span
            v-if="!isCreateMode"
            v-bk-tooltips="{
              content: t('请选择业务'),
              disabled: !!bizId
            }"
            class="inline-block">
            <BkButton
              :disabled="!bizId"
              text
              @click="handleCreateGroup">
              <i class="db-icon-plus-circle mr-4" />
              {{ $t('新建分组') }}
            </BkButton>
          </span>
          <BkForm
            v-else
            ref="formRef"
            :model="createState">
            <BkFormItem
              class="create-group"
              error-display-type="tooltips"
              property="name"
              required
              :rules="rules">
              <BkInput
                ref="inputRef"
                v-model="createState.name"
                class="create-input"
                :maxlength="64"
                :placeholder="$t('以小写英文字符开头_且只能包含英文字母_数字_连字符')"
                show-word-limit
                @enter="handleConfirm" />
              <a
                class="create-button create-button-confirm"
                href="javascript:">
                <DbIcon
                  type="check-line"
                  @click="handleConfirm" />
              </a>
              <a
                class="create-button create-button-close"
                href="javascript:">
                <DbIcon
                  type="close"
                  @click="handleClose" />
              </a>
            </BkFormItem>
          </BkForm>
        </div>
      </template>
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { createGroup, getGroupList } from '@services/influxdbGroup';
  import type { InfluxDBGroupItem } from '@services/types/influxdbGroup';

  import { nameRegx } from '@common/regex';

  interface Emits {
    (e: 'update:model-value', value: number): void,
    (e: 'change', value: {
      id: number,
      name: string
    }): void,
  }

  interface Props {
    modelValue: number | string,
    bizId: number | string,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();

  let isInit = true;
  const localGroupId = ref<number | string>('');
  const groupList = shallowRef<Array<InfluxDBGroupItem>>([]);
  const isLoading = ref(false);

  watch(() => props.modelValue, () => {
    localGroupId.value = props.modelValue;
  }, { immediate: true });

  watch(() => props.bizId, (id) => {
    if (id) {
      fetchGroupList();
    } else {
      groupList.value = [];
    }
  }, { immediate: true });

  const fetchGroupList = (id?: number) => {
    isLoading.value = true;
    getGroupList({ bk_biz_id: Number(props.bizId) })
      .then((data) => {
        groupList.value = data.results;

        const groupId = Number(route.query.groupId);
        if (isInit && groupId && groupList.value.find(item => item.id === groupId)) {
          handleChangeId(groupId);
          return;
        }

        if (id) {
          handleChangeId(id);
        }
      })
      .catch(() => {
        groupList.value = [];
      })
      .finally(() => {
        isLoading.value = false;
        isInit = false;
      });
  };

  const handleChangeId = (id: number) => {
    emits('update:model-value', id);
    emits('change', { id, name: groupList.value.find(item => item.id === id)?.name ?? '' });
  };

  // 新建分组功能
  const formRef = ref();
  const inputRef = ref();
  const isCreateMode = ref(false);
  const isCreating = ref(false);
  const createState = reactive({
    name: '',
  });
  const rules = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'change',
    },
  ];

  const handleCreateGroup = () => {
    isCreateMode.value = true;
    nextTick(() => {
      inputRef.value?.focus?.();
    });
  };

  const handleClose = () => {
    formRef.value?.clearValidate?.();
    createState.name = '';
    isCreateMode.value = false;
  };

  const handleConfirm = () => {
    if (isCreating.value) return;

    formRef.value.validate()
      .then(() => {
        isCreating.value = true;
        createGroup({
          name: createState.name,
          bk_biz_id: Number(props.bizId),
        })
          .then((data) => {
            fetchGroupList(data.id);
            handleClose();
          })
          .finally(() => {
            isCreating.value = false;
          });
      });
  };

  const handleToggleSelector = (isShow: boolean) => {
    if (!isShow) {
      handleClose();
    }
  };
</script>

<style lang="less" scoped>
.create-group {
  flex: 1;
  padding-left: 8px;

  :deep(.bk-form-content) {
    display: flex;
    width: 100%;
    align-items: center;

    .bk-form-error-tips {
      right: 62px;
    }
  }

  .create-input {
    width: unset;
    flex: 1;
  }

  .create-button {
    font-size: 18px;
    flex-shrink: 0;

    &-confirm {
      margin-left: 8px;
    }

    &-close {
      margin: 0 2px;
      font-size: 24px;
      color: #c4c6cc;
    }
  }
}
</style>
