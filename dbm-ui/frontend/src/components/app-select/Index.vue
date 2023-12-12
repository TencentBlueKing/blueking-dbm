<template>
  <AppSelect
    :data="withFavorBizList"
    :generate-key="(item: IAppItem) => item.bk_biz_id"
    :generate-name="(item: IAppItem) => item.display_name"
    style="margin: 0 12px"
    theme="dark"
    :value="currentBiz"
    @change="handleAppChange">
    <template #default="{ data }">
      <AuthComponent
        action-id="DB_MANAGE"
        :permission="data.permission.db_manage"
        :resource-id="data.bk_biz_id"
        resource-type="BUSINESS">
        <div class="db-app-select-item">
          <div>{{ data.name }} (#{{ data.bk_biz_id }})</div>
          <div style="margin-left: auto;">
            <DbIcon
              v-if="favorBizIdMap[data.bk_biz_id]"
              class="unfavor-btn"
              style="color: #ffb848;"
              type="star-fill"
              @click.stop="handleUnfavor(data.bk_biz_id)" />
            <DbIcon
              v-else
              class="favor-btn"
              type="star"
              @click.stop="handleFavor(data.bk_biz_id)" />
          </div>
        </div>
        <template #forbid>
          <div class="db-app-select-item no-permission">
            <div>{{ data.name }} (#{{ data.bk_biz_id }})</div>
            <div style="margin-left: auto;">
              <DbIcon
                v-if="favorBizIdMap[data.bk_biz_id]"
                class="unfavor-btn"
                style="color: #ffb848;"
                type="star-fill"
                @click.stop="handleUnfavor(data.bk_biz_id)" />
              <DbIcon
                v-else
                class="favor-btn"
                type="star"
                @click.stop="handleFavor(data.bk_biz_id)" />
            </div>
          </div>
        </template>
      </AuthComponent>
    </template>
  </AppSelect>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    shallowRef,
  } from 'vue';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import { getBizs } from '@services/source/cmdb';

  import {
    useGlobalBizs,
    useUserProfile,
  } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { makeMap } from '@utils';

  import AppSelect from '@blueking/app-select';

  import '@blueking/app-select/dist/style.css';

  type IAppItem = ServiceReturnType<typeof getBizs>[number]

  const route = useRoute();
  const router = useRouter();
  const userProfile = useUserProfile();

  const {
    bizs: bizList,
  } = useGlobalBizs();

  const favorBizIdMap = shallowRef(makeMap(userProfile.profile[UserPersonalSettings.APP_FAVOR] || []));

  const currentBiz = computed(() => _.find(bizList, item => item.bk_biz_id === window.PROJECT_CONFIG.BIZ_ID));
  const withFavorBizList = computed(() => _.sortBy(bizList, item => favorBizIdMap.value[item.bk_biz_id]));

  const handleAppChange = (appInfo: IAppItem) => {
    const {
      bk_biz_id: bkBizId,
    } = appInfo;

    const pathRoot = `/${bkBizId}`;
    if (!window.PROJECT_CONFIG.BIZ_ID) {
      window.location.href = pathRoot;
      return;
    }

    const reload = (targetPath: string) => {
      setTimeout(() => {
        const path = targetPath.replace(/^\/[\d]+/, pathRoot);
        window.location.href = path;
      }, 100);
    };
    // 1，当前路由不带参数，切换业务时停留在当前页面
    let currentRouteHasNotParams = true;
    Object.keys(route.params).forEach((paramKey) => {
      if (route.params[paramKey] === undefined || route.params[paramKey] === null) {
        return;
      }
      currentRouteHasNotParams = false;
    });
    if (currentRouteHasNotParams) {
      reload(route.path);
      return;
    }
    const { matched } = route;
    // 2，当前路由带有请求参数，切换业务时则需要做回退处理
    // 路由只匹配到了一个
    if (matched.length < 2) {
      const [{ path }] = matched;
      reload(path);
      return;
    }

    // 路由有多层嵌套
    const {
      path,
      redirect,
    } = matched[1];
    // 重定向到指定的路由path
    if (_.isString(redirect)) {
      reload(redirect);
      return;
    }
    // 重定向到指定的路由name
    if (redirect && _.isPlainObject(redirect)) {
      const redirectName = (redirect as {name: string}).name;
      if (redirectName) {
        const route = router.resolve({
          name: redirectName,
        });
        reload(route.href);
        return;
      }
    }
    reload(path);
  };

  const handleUnfavor = (bizId: number) => {
    const lastFavorBizIdMap = { ...favorBizIdMap.value };
    delete lastFavorBizIdMap[bizId];
    favorBizIdMap.value = lastFavorBizIdMap;

    userProfile.updateProfile({
      label: UserPersonalSettings.APP_FAVOR,
      values: Object.keys(lastFavorBizIdMap),
    });
  };

  const handleFavor = (bizId: number) => {
    favorBizIdMap.value = {
      ...favorBizIdMap.value,
      [bizId]: true,
    };
    userProfile.updateProfile({
      label: UserPersonalSettings.APP_FAVOR,
      values: Object.keys(favorBizIdMap.value),
    });
  };
</script>
<style lang="less">
.db-app-select-item{
  display: flex;
  align-items: center;
  width: 100%;

  &:hover{
    .favor-btn{
      opacity: 100%;
    }
  }

  .favor-btn{
    opacity: 0%;
    transition: all .1s;
  }
}

.tippy-box[data-theme="bk-app-select-menu"]{
  border: none !important;
  box-shadow: 0 2px 3px 0 rgb(0 0 0 / 10%) !important;
}
</style>
