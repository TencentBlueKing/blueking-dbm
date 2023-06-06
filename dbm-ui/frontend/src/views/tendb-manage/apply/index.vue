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
  <SmartAction class="apply-tendb">
    <DbForm
      ref="formRef"
      auto-label-width
      class="mb-16"
      :label-width="216"
      :model="formData">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:biz-id="formData.bk_biz_id"
          v-model:db_app_abbr="formData.details.db_app_abbr" />
        <ClusterName
          v-model="formData.details.cluster_name" />
        <ClusterAlias
          v-model="formData.details.cluster_alias" />
        <CloudItem
          v-model="formData.details.bk_cloud_id" />
      </DbCard>
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('DB版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="formData.details.db_version"
            class="item-input"
            filterable
            :input-search="false"
            :loading="isDbVersionLoading">
            <BkOption
              v-for="item in dbVersionList"
              :key="item"
              :label="item"
              :value="item" />
            <template #extension>
              <span class="create-version"><i class="bk-icon icon-plus-circle" />新建模板</span>
            </template>
          </BkSelect>
          <div class="tap-db-module item-input">
            <p>
              <span>Mysql版本 : &nbsp;</span>
              <span>Mysql 5.0</span>
            </p>
            <p>
              <span>Spider : &nbsp;</span>
              <span>Spider 5.0</span>
            </p>
            <p>
              <span>字符集 : &nbsp;</span>
              <span>UTF-8</span>
            </p>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="$t('集群分片数')"
          property="details.cluster_fragmentation"
          required>
          <BkSelect
            v-model="formData.details.cluster_fragment"
            class="item-input"
            filterable
            :input-search="false"
            :loading="isFragmentLoading">
            <BkOption
              v-for="item in fragmentList"
              :key="item"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="$t('存储层（RemoteDB / DR）部署方案')"
          property="details.cluster_capacity"
          required>
          <BkSelect
            v-model="formData.details.cluster_capacity"
            class="item-input"
            filterable
            :input-search="false"
            :loading="isCapacityLoading">
            <BkOption
              v-for="item in capacityList"
              :key="item"
              :label="item"
              :value="item"
              @mouseenter="handleEnter(item)"
              @mouseleave="handleLeave" />
            <img
              v-if="hoverImgUrl"
              :src="hoverImgUrl">
          </BkSelect>
          <span class="input-tips">集群容量（分片大小 x 分片数）</span>
        </BkFormItem>
        <BkFormItem
          :label="$t('接入层 （Master）')"
          required>
          <div class="tap-as-module">
            <table>
              <tr class="as-block">
                <td>{{ $t('规则') }}</td>
                <td>
                  <BkFormItem
                    property="details.as_specification"
                    required>
                    <BkSelect
                      v-model="formData.details.as_specification"
                      filterable
                      :input-search="false"
                      :loading="isDbVersionLoading"
                      style="width:314px">
                      <BkOption
                        v-for="item in dbVersionList"
                        :key="item"
                        :label="item"
                        :value="item" />
                    </BkSelect>
                  </BkFormItem>
                </td>
              </tr>
              <tr class="as-block">
                <td>{{ $t('数量') }}</td>
                <td>
                  <BkFormItem
                    property="details.as_number"
                    required>
                    <NumberInput
                      v-model="formData.details.as_number"
                      style="background-color: #fff;width: 314px" />
                    <span class="input-desc">{{ $t('至少1台') }}</span>
                  </BkFormItem>
                </td>
              </tr>
            </table>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="$t('访问端口')"
          property="details.port"
          required>
          <NumberInput
            v-model="formData.details.port"
            style="background-color: #fff;width: 184px" />
        </BkFormItem>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="formData.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px;"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
    <template #action>
      <div>
        <BkButton
          :loading="baseState.isSubmitting"
          style="width: 88px;"
          theme="primary"
          @click="handleSubmit">
          {{ $t('提交') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleReset">
          {{ $t('重置') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ $t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
</template>

  <script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useApplyBase, useInfo } from '@hooks';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';

  import { getInitFormData } from '../common/base';

  import NumberInput from './components/numberInput.vue';

  import CloudItem from '@/components/apply-items/CloudItem.vue';
  import ClusterAlias from '@/components/apply-items/ClusterAlias.vue';
  import ClusterName from '@/components/apply-items/ClusterName.vue';


  const { t } = useI18n();
  const {
    baseState,
    handleCancel,
  } = useApplyBase();

  const formData = reactive(getInitFormData());
  const hoverImgUrl = ref('');
  const formRef = ref();

  const handleEnter = (item: any) => {
    hoverImgUrl.value = item;
  };
  const handleLeave = () => {
    hoverImgUrl.value = '';
  };


  /**
   * Tendb 版本处理
   */
  const isDbVersionLoading = ref(true);
  const dbVersionList = shallowRef<Array<string>>([]);


  /**
   * 集群分片数处理
   *
   */
  const isFragmentLoading = ref(true);
  const fragmentList = shallowRef<Array<string>>([]);


  /**
   * 部署方案
   *
   */
  const isCapacityLoading = ref(true);
  const capacityList = shallowRef<Array<string>>([]);


  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        baseState.isSubmitting = true;
      });
  };

  /**
   * 重置表单
   */
  const handleReset = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, getInitFormData());
        formRef.value.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };
  </script>

  <style lang="less" scoped>
  .apply-tendb {
    display: block;
    .create-version {
        margin-left: 30px;
      }
    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }

    :deep(.item-input) {
      width: 435px;
    }

    .service-item {
      :deep(.bk-form-label) {
        &::after {
          content: "";
        }
      }
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 18px;
      color: #63656e;
    }
    .input-tips {
      font-size: 12px;
      color: #979BA5;
      letter-spacing: 0;
      line-height: 20px;
    }
    .tap-db-module {
      width: 433px;
      height: 76px;
      margin-top: 12px;
      padding: 8px 32px;
      font-size: 12px;
      background: #f5f7fa;
      color: #63656E;
      line-height: 20px;
       p {
        span {
          display:inline-block
        }
        span:first-child {
          width: 75px;
          text-align: right;
       }
      }
    }
    .tap-as-module {
      width: 655px;
      height: 132px;
      padding: 16px 10px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;

      table {
        td:nth-child(2) {
          padding: 0 12px 0 8px;
        }
        td:first-child {
          width: 70px;
          text-align: right;
          padding-right: 14px;
          &::after{
            position: absolute;
            width: 14px;
            color: #ea3636;
            text-align: center;
            content: "*";
          }
        }
        tr:nth-child(n+2) {
          td {
            padding-top: 24px;
          }
        }
      }

  }
}
</style>
