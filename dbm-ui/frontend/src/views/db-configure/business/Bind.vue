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
  <div class="config-bind">
    <DbForm
      ref="bindFormRef"
      class="config-bind__form"
      :label-width="168"
      :model="formData">
      <DbCard :title="$t('绑定数据库配置')">
        <BkFormItem
          :label="$t('数据库类型')"
          required>
          <BkTag
            class="type-item"
            theme="info"
            type="stroke">
            <template #icon>
              <i class="db-icon-mysql mr-5" />
            </template>
            {{ mysqlTypeName }}
          </BkTag>
        </BkFormItem>
        <BkFormItem
          :label="$t('数据库版本')"
          property="version"
          required>
          <BkSelect
            v-model="formData.version"
            :clearable="false"
            filterable
            :input-search="false"
            :loading="versionState.loading"
            :placeholder="$t('请选择数据库版本')">
            <BkOption
              v-for="(item, index) in versionState.list"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="$t('字符集')"
          property="character_set"
          required>
          <BkSelect
            v-model="formData.character_set"
            :clearable="false"
            filterable
            :input-search="false"
            :placeholder="$t('请选择字符集')">
            <BkOption
              v-for="(item, index) in characterList"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
      </DbCard>
    </DbForm>
    <div class="absolute-footer">
      <BkButton
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('立即绑定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ $t('取消') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { saveModulesDeployInfo } from '@services/source/configs';
  import { getVersions } from '@services/versionFiles';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, mysqlType } from '@common/const';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const type = computed(() => route.params.clusterType as ClusterTypes);
  const mysqlTypeName = computed(() => {
    const target = Object.values(mysqlType).find(item => item.type === type.value);
    return target?.name || '';
  });

  const isSubmitting = ref(false);
  const formData = reactive({
    version: '',
    character_set: '',
  });
  const characterList = ['utf8', 'utf8mb4', 'gbk', 'latin1'];
  const versionState = reactive({
    list: [] as string[],
    loading: false,
  });

  /**
   * 获取版本列表
   */
  const fetchVersions = () => {
    const params = {
      query_key: type.value,
      db_type: 'mysql',
    };
    versionState.loading = true;
    getVersions(params)
      .then((res) => {
        versionState.list = res;
      })
      .finally(() => {
        versionState.loading = false;
      });
  };
  fetchVersions();

  const handleCancel = () => {
    router.go(-1);
  };

  const bindFormRef = ref();
  const handleSubmit = async () => {
    const validate = await bindFormRef.value.validate()
      .then(() => true)
      .catch(() => false);
    if (!validate) return;

    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      level_name: 'module',
      level_value: Number(route.params.moduleId),
      meta_cluster_type: type.value,
      version: 'deploy_info',
      conf_type: 'deploy',
      conf_items: [
        {
          description: '字符集',
          conf_name: 'charset',
          conf_value: formData.character_set,
          op_type: 'add',
        },
        {
          description: '数据库版本',
          conf_name: 'db_version',
          conf_value: formData.version,
          op_type: 'add',
        },
      ],
    };
    isSubmitting.value = true;
    saveModulesDeployInfo(params)
      .then(() => {
        Message({
          message: t('绑定成功'),
          theme: 'success',
        });
        window.changeConfirm = false;
        handleCancel();
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>

<style lang="less" scoped>
  .config-bind {
    &__form {
      .type-item {
        height: 30px;
      }

      .bk-form-item {
        max-width: 690px;
      }
    }
  }
</style>
