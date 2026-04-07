<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="platform-detail-page">
    <div class="platform-detail-content db-scroll-y">
      <!-- 基础信息 -->
      <DbCard
        mode="collapse"
        :title="t('基础信息')">
        <BkLoading :loading="loading">
          <BkForm class="base-info-form">
            <div class="base-info-form-row">
              <BkFormItem :label="t('配置名称')">
                {{ detailData.name || '--' }}
              </BkFormItem>
              <BkFormItem :label="t('配置文件')">
                {{ detailData.version || '--' }}
              </BkFormItem>
            </div>
            <div class="base-info-form-row">
              <BkFormItem :label="t('最近更新人')">
                {{ detailData.updated_by || '--' }}
              </BkFormItem>
              <BkFormItem :label="t('更新时间')">
                {{ detailData.updated_at || '--' }}
              </BkFormItem>
            </div>
            <div class="base-info-form-row">
              <BkFormItem :label="t('描述')">
                {{ detailData.description || '--' }}
              </BkFormItem>
            </div>
          </BkForm>
        </BkLoading>
      </DbCard>

      <!-- 参数信息 -->
      <DbCard
        class="mt-16"
        mode="collapse"
        :title="t('参数信息')">
        <div class="param-operations mb-16">
          <BkButton
            theme="primary"
            @click="isShowAddParam = true">
            {{ t('新增参数') }}
          </BkButton>
        </div>
        <BkLoading :loading="paramLoading">
          <DbTable
            ref="paramTableRef"
            :data-source="paramDataSource"
            fixed-pagination
            row-key="conf_name">
            <TableColumn
              col-key="conf_name"
              :title="t('参数名')"
              :width="200" />
            <TableColumn
              col-key="value_default"
              :title="t('默认值')"
              :width="150">
              <template #default="{ row }">
                {{ row.value_default ?? '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="conf_value"
              :title="t('当前值')"
              :width="200">
              <template #default="{ row }">
                {{ row.conf_value ?? '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="value_allowed"
              :title="t('约束值')"
              :width="150">
              <template #default="{ row }">
                {{ row.value_allowed || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="description"
              ellipsis
              :title="t('描述')"
              :width="200">
              <template #default="{ row }">
                {{ row.description || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="need_restart"
              :title="t('重启生效')"
              :width="100">
              <template #default="{ row }">
                <span :class="row.need_restart === 1 ? 'restart-icon-yes' : 'restart-icon-no'">
                  <DbIcon :type="row.need_restart === 1 ? 'check-line' : 'close'" />
                </span>
              </template>
            </TableColumn>
          </DbTable>
        </BkLoading>
      </DbCard>
    </div>

    <!-- 新增参数侧滑 -->
    <BkSideslider
      :is-show="isShowAddParam"
      quick-close
      :title="t('新增参数')"
      :width="640"
      @closed="isShowAddParam = false">
      <div class="add-param-content">
        <BkForm
          ref="addFormRef"
          form-type="vertical"
          :model="addParamForm">
          <BkFormItem
            :label="t('参数名')"
            property="conf_name"
            required>
            <BkSelect
              v-model="addParamForm.conf_name"
              :clearable="false"
              filterable
              :placeholder="t('请选择参数')">
              <BkOption
                v-for="param of availableParams"
                :key="param.conf_name"
                :label="param.conf_name"
                :value="param.conf_name" />
            </BkSelect>
          </BkFormItem>
          <BkFormItem
            :label="t('参数值')"
            property="conf_value"
            required>
            <BkInput
              v-model="addParamForm.conf_value"
              :placeholder="t('请输入参数值')" />
          </BkFormItem>
          <BkFormItem :label="t('描述')">
            <BkInput
              v-model="addParamForm.description"
              :placeholder="t('请输入描述')"
              type="textarea" />
          </BkFormItem>
        </BkForm>
      </div>
      <template #footer>
        <BkButton
          class="mr-8"
          :loading="submitLoading"
          theme="primary"
          @click="handleAddParamConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton @click="isShowAddParam = false">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkSideslider>
  </div>
  <Teleport to="#dbContentTitleAppend">
    <span class="config-detail-nav-title">
      {{ configTypeName }}
    </span>
    <span class="config-detail-nav-desc">
      {{ detailData.name || '' }}
    </span>
  </Teleport>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import {
    getConfigBaseDetails,
    getConfigNames,
    getListConfTypes,
    updatePlatformConfig,
  } from '@services/source/configs';

  import DbTable from '@components/db-table/IndexNew.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const paramTableRef = ref<InstanceType<typeof DbTable>>();
  const addFormRef = ref();

  const configTypeName = ref('');

  const { clusterType, confType, version } = route.params as {
    clusterType: string;
    confType: string;
    version: string;
  };

  // 获取 confType 对应的显示名称
  useRequest(getListConfTypes, {
    defaultParams: [{ meta_cluster_type: clusterType }],
    onSuccess(res) {
      const matched = res.find((item) => item.conf_type === confType);
      configTypeName.value = matched?.name || confType;
    },
  });

  type DetailResult = ServiceReturnType<typeof getConfigBaseDetails>;
  const detailData = ref<Partial<DetailResult>>({});
  const allConfItems = ref<DetailResult['conf_items']>([]);

  // 获取配置详情
  const { loading, run: fetchDetail } = useRequest(getConfigBaseDetails, {
    defaultParams: [
      {
        conf_type: confType,
        meta_cluster_type: clusterType,
        version: version,
      },
    ],
    onSuccess(res) {
      detailData.value = res;
      allConfItems.value = res.conf_items || [];
      nextTick(() => paramTableRef.value?.fetchData({}, true));
    },
  });

  const paramLoading = ref(false);

  const paramDataSource = (params: { limit: number; offset: number }) => {
    const data = allConfItems.value;
    const start = params.offset;
    const end = start + params.limit;
    return Promise.resolve({
      count: data.length,
      results: data.slice(start, end),
    });
  };

  // 新增参数
  const isShowAddParam = ref(false);
  const submitLoading = ref(false);
  const addParamForm = reactive({
    conf_name: '',
    conf_value: '',
    description: '',
  });
  const availableParams = ref<ServiceReturnType<typeof getConfigNames>>([]);

  // 获取可选参数名
  useRequest(getConfigNames, {
    defaultParams: [
      {
        conf_type: confType,
        meta_cluster_type: clusterType,
        version: version,
      },
    ],
    onSuccess(res) {
      availableParams.value = res;
    },
  });

  const handleAddParamConfirm = async () => {
    try {
      await addFormRef.value?.validate();
    } catch {
      return;
    }

    submitLoading.value = true;
    try {
      await updatePlatformConfig({
        conf_items: [
          {
            ...addParamForm,
            conf_name: addParamForm.conf_name,
            conf_value: addParamForm.conf_value,
            description: addParamForm.description,
            op_type: 'add',
          } as any,
        ],
        conf_type: confType,
        confirm: 0,
        description: '',
        meta_cluster_type: clusterType,
        name: detailData.value.name || '',
        version: version,
      });
      isShowAddParam.value = false;
      addParamForm.conf_name = '';
      addParamForm.conf_value = '';
      addParamForm.description = '';
      fetchDetail({
        conf_type: confType,
        meta_cluster_type: clusterType,
        version: version,
      });
    } finally {
      submitLoading.value = false;
    }
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'PlatformDbConfigureList',
      });
    },
  });
</script>

<style lang="less" scoped>
  .config-detail-nav-title {
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 16px;
    line-height: 24px;
  }

  .config-detail-nav-desc {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;
  }

  .config-detail-nav-desc::before {
    position: absolute;
    top: 50%;
    left: 0;
    width: 1px;
    height: 16px;
    content: '';
    background: #dcdee5;
    transform: translateY(-50%);
  }

  .platform-detail-content {
    height: calc(100vh - var(--notice-height) - 100px);
    padding: 24px;
  }

  .base-info-form {
    display: flex;
    flex-direction: column;
    padding: 16px 24px;
    background: #fff;
    border-radius: 2px;
  }

  .base-info-form-row {
    display: flex;
    width: 100%;

    :deep(.bk-form-item) {
      flex: 1;
      margin-bottom: 0;
    }
  }

  .param-operations {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .add-param-content {
    padding: 24px;
  }

  .restart-icon-yes,
  .restart-icon-no {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
  }

  .restart-icon-yes {
    font-size: 12px;
    color: #65c389;
    background: #ebfaf0;
  }

  .restart-icon-no {
    font-size: 16px;
    color: #ff5656;
    background: #ffebeb;
  }
</style>
