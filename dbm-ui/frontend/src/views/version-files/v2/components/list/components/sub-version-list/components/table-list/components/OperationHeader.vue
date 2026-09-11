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
  <div
    v-if="!isEditName"
    class="version-file-operation-header">
    <div class="title-main">
      <span>{{ versionName || '--' }}</span>
      <BkTag
        class="ml-12"
        radius="12px">
        {{ dbVersionListCount }}
      </BkTag>
    </div>
    <!-- 外层拦掉冒泡，避免点击操作项时把所在的系列折叠面板一起收起 -->
    <div
      class="more-operate"
      @click.stop>
      <BkDropdown trigger="click">
        <div class="icon-wrapper">
          <DbIcon type="more" />
        </div>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <AuthButton
                action-id="package_manage"
                :permission="permission"
                :resource="dbType"
                text
                @click="handleAddVersion">
                {{ t('添加版本') }}
              </AuthButton>
            </BkDropdownItem>
            <BkDropdownItem
              v-bk-tooltips="{
                content: t('该版本系列下存在 n 个版本，请删除后再操作', { n: dbVersionListCount }),
                placement: 'right',
                disabled: dbVersionListCount === 0,
              }">
              <AuthButton
                action-id="package_manage"
                :disabled="dbVersionListCount > 0"
                :permission="permission"
                :resource="dbType"
                text
                @click="handleEditName">
                {{ t('编辑系列') }}
              </AuthButton>
            </BkDropdownItem>
            <BkDropdownItem
              v-bk-tooltips="{
                content: t('该版本系列下存在 n 个版本，请删除后再操作', { n: dbVersionListCount }),
                placement: 'right',
                disabled: dbVersionListCount === 0,
              }">
              <DbPopconfirm
                :confirm-handler="handleDeleteVersionSeries"
                :confirm-text="t('删除')"
                :content="t('删除操作无法撤回，请谨慎操作！')"
                :disabled="dbVersionListCount > 0"
                placement="bottom"
                theme="danger"
                :title="t('确认删除该版本系列？')">
                <AuthButton
                  action-id="package_manage"
                  :disabled="dbVersionListCount > 0"
                  :permission="permission"
                  :resource="dbType"
                  text>
                  {{ t('删除系列') }}
                </AuthButton>
              </DbPopconfirm>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
  </div>
  <EditSeries
    v-else
    v-model:is-edit="isEditName"
    class="operation-header-edit-series-main"
    :data="versionName"
    :distribution-id="data?.distribution"
    :existed-list="existedVersionNameList"
    mode="update"
    :series-id="data?.id"
    @confirm="handleConfirmChangeVersionName" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteVersionSeries } from '@services/source/version';

  import { messageSuccess } from '@utils';

  import EditSeries from '../../EditSeries.vue';

  interface Props {
    data?: {
      distribution: number;
      id: number;
      name: string;
    };
    dbType: string;
    dbVersionListCount?: number;
    existedVersionNameList: string[];
    permission?: boolean;
  }

  interface Emits {
    (e: 'addNewVersion'): void;
    (e: 'editVersionSeries'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    dbVersionListCount: 0,
    permission: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isEditName = ref(false);
  const versionName = ref('');

  const { runAsync: runDeleteVersionSeries } = useRequest(deleteVersionSeries, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('editVersionSeries');
    },
  });

  watch(
    () => props.data,
    () => {
      versionName.value = props.data?.name || '';
    },
    {
      immediate: true,
    },
  );

  // 返回 Promise 交给 DbPopconfirm，由它接管确认按钮 loading 与请求成功后的关闭
  const handleDeleteVersionSeries = () =>
    runDeleteVersionSeries({
      distribution: props.data!.distribution,
      id: props.data!.id,
    });

  const handleConfirmChangeVersionName = (id: number, name: string) => {
    versionName.value = name;
    emits('editVersionSeries');
  };

  const handleEditName = () => {
    isEditName.value = true;
  };

  const handleAddVersion = () => {
    emits('addNewVersion');
  };
</script>
<style lang="less">
  .version-file-operation-header {
    display: flex;
    align-items: center;

    .title-main {
      font-size: 16px;
      font-weight: 700;
      color: #313238;
    }

    .more-operate {
      display: flex;
      margin-left: 4px;

      .icon-wrapper {
        display: flex;
        width: 26px;
        height: 26px;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        &:hover {
          background: #dcdee5;
        }
      }
    }
  }

  .operation-header-edit-series-main {
    .edit-main {
      padding: 0;

      .edit-input-main {
        max-width: 500px;
      }
    }
  }
</style>
