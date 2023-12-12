<template>
  <BkLoading :loading="isLoading">
    <div
      v-bk-tooltips="t('添加数据库组件')"
      class="navigation-database-module-config-btn"
      @click="handleShowModuleConfig">
      <DbIcon type="add" />
    </div>
  </BkLoading>
  <BkDialog
    v-model:isShow="isShow"
    class="navigation-database-module-config-dialog"
    :width="940">
    <div class="content-wrapper">
      <div class="select-wrapper">
        <div class="select-header">
          <div class="title">
            {{ t('添加数据库组件') }}
          </div>
        </div>
        <div class="select-list">
          <div
            v-for="groupName in Object.keys(configMap)"
            :key="groupName"
            class="module-col">
            <div class="module-title">
              {{ groupName }}
            </div>
            <div
              v-for="item in configMap[groupName]"
              :key="item.name"
              class="item"
              @click="handleSelect(item.value)">
              <DbIcon
                style="margin-right: 8px; font-size: 16px; color: #979BA5"
                :type="item.icon" />
              <span>{{ item.name }}</span>
              <BkCheckbox
                :model-value="selectList.includes(item.value)"
                @change="handleSelect(item.value)" />
            </div>
          </div>
        </div>
      </div>
      <div class="result-wrapper">
        <div class="result-header">
          <I18nT keypath="已添加 （n）">
            {{ selectList.length }}
          </I18nT>
        </div>
        <div style="height: 290px">
          <ScrollFaker>
            <Vuedraggable
              v-model="selectList"
              item-key="value">
              <template #item="{element: item}">
                <div
                  v-if="configValueMap[item]"
                  class="result-item">
                  <DbIcon
                    class="mr-8"
                    style="color: #979BA5; cursor: move;"
                    type="drag" />
                  <DbIcon
                    class="mr-8"
                    style="font-size: 16px; color: #979BA5"
                    :type="configValueMap[item].icon" />
                  <span>{{ configValueMap[item].name }}</span>
                  <DbIcon
                    class="remove-btn"
                    type="close"
                    @click="handleSelect(configValueMap[item].value)" />
                </div>
              </template>
            </Vuedraggable>
          </ScrollFaker>
        </div>
      </div>
    </div>
    <template #footer>
      <BkButton
        style="width: 66px"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 66px"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import Vuedraggable from 'vuedraggable';

  import {
    getBizSettingList,
    updateBizSetting,
  } from '@services/system-setting';

  import { messageSuccess } from '@utils';

  const DATABASE_MANAGE_MENU = 'DATABASE_MANAGE_MENU';

  const { t } = useI18n();

  const configMap = {
    [t('关系型数据库')]: [
      {
        name: 'MySQL',
        value: 'mysql',
        icon: 'mysql',
      },
      {
        name: 'Tendb Cluster',
        value: 'tendbCluster',
        icon: 'mysql',
      },
    ],
    [t('NoSQL 数据库')]: [
      {
        name: 'Redis',
        value: 'redis',
        icon: 'redis',
      },
      // {
      //   name: 'MongoDB',
      //   value: 'mongoDB',
      //   icon: 'mysql',
      // },
    ],
    [t('时序数据库')]: [
      {
        name: 'influxDB',
        value: 'influxdb',
        icon: 'influxdb',
      },
    ],
    [t('消息队列')]: [
      {
        name: 'Pulsar',
        value: 'pulsar',
        icon: 'pulsar',
      },
      {
        name: 'Kafka',
        value: 'kafka',
        icon: 'kafka',
      },
    ],
    [t('大数据存储')]: [
      {
        name: 'ElasticSearch',
        value: 'es',
        icon: 'es',
      },
      {
        name: 'HDFS',
        value: 'hdfs',
        icon: 'hdfs',
      },
    ],
  };

  const configValueMap = Object.values(configMap).reduce((result, configItem) => {
    configItem.forEach(item => Object.assign(result, { [item.value]: item }));
    return result;
  }, {} as Record<string, ValueOf<typeof configMap>[number]>);

  const modelValue = defineModel<string[]>({
    default: [],
    local: true,
  });

  const isShow = ref(false);
  const isSubmiting = ref(false);
  const selectList = ref<string[]>([]);

  watch(modelValue, () => {
    selectList.value = [...modelValue.value];
  }, {
    immediate: true,
  });

  const {
    loading: isLoading,
  } = useRequest(getBizSettingList, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        key: DATABASE_MANAGE_MENU,
      },
    ],
    onSuccess(data) {
      modelValue.value = data[DATABASE_MANAGE_MENU] && data[DATABASE_MANAGE_MENU].length > 0 ? data[DATABASE_MANAGE_MENU] : ['mysql'];
    },
  });

  const handleShowModuleConfig = () => {
    isShow.value = true;
  };

  const handleSelect = (value: string) => {
    const index = selectList.value.indexOf(value);
    if (index > -1) {
      selectList.value.splice(index, 1);
    } else {
      selectList.value.push(value);
    }
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    isShow.value = false;
    updateBizSetting({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      key: DATABASE_MANAGE_MENU,
      value: [...selectList.value],
    }).then(() => {
      modelValue.value = [...selectList.value];
      messageSuccess(t('保存成功'));
    })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleCancel = () => {
    isShow.value = false;
  };

</script>
<style lang="less">
.navigation-database-module-config-btn{
  display: flex;
  height: 24px;
  padding: 0 10px;
  margin-top: 8px;
  margin-right: 10px;
  margin-left: 10px;
  font-size: 14px;
  color: #63656E;
  cursor: pointer;
  background: #2C323F;
  border-radius: 4px;
  justify-content: center;
  align-items: center;
  transition: all .1s;

  &:hover{
    background: #363B48;
  }
}

.navigation-database-module-config-dialog{
  .bk-modal-header{
    display: none;
  }

  .bk-modal-content{
    padding: 0 !important;
  }

  .content-wrapper {
    display: flex;
  }

  .select-wrapper{
    flex: 1;

    .select-header{
      display: flex;
      height: 48px;
      padding-right: 50px;
      padding-left: 24px;
      margin-bottom: 24px;
      align-items: center;

      .title{
        font-size: 20px;
        color: #313238;
      }
    }
  }

  .select-list{
    display: flex;
    padding-bottom: 20px;
    flex-wrap: wrap;
    font-size: 14px;
    color: #313238;

    .module-col{
      flex: 0 0 25%;
      padding: 0 15px;
      margin-bottom: 24px;
      border-radius: 2px;

      .module-title{
        padding-left: 8px;
        margin-bottom: 10px;
        font-weight: bold;
        line-height: 1.5;
      }

      .item{
        display: flex;
        height: 32px;
        padding: 0 8px;
        cursor: pointer;
        transition: .1s;
        align-items: center;

        &:hover{
          background: #F0F1F5;
        }

        .bk-checkbox{
          margin-left: auto;
        }
      }
    }
  }

  .result-wrapper{
    font-size: 14px;
    color:#63656E;
    border-left: 1px solid #F0F1F5;
    flex: 0 0 200px;

    .result-header{
      padding: 18px 16px 12px;
      font-size: 14px;
      color: #313238;
    }

    .result-item{
      display: flex;
      height: 36px;
      padding-right: 10px;
      padding-left: 16px;
      cursor: default;
      transition: .1s;
      align-items: center;

      &:hover{
        background: #F5F7FA;

        .remove-btn{
          opacity: 100%;
        }
      }
    }

    .remove-btn{
      margin-left: auto;
      font-size: 20px;
      color: #979BA5;
      cursor: pointer;
      opacity: 0%;

      &:hover{
        color: #3a84ff;
      }
    }
  }
}

</style>
