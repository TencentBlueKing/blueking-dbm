/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package testsuite

import (
	"context"
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/suite"

	"github.com/stretchr/testify/assert"
)

var addSql = "INSERT INTO `bkdata_basic`.`auth_user_role`" +
	"( `user_id`, `role_id`, `scope_id`, `auth_status`, `expired_date`, `created_by`, `created_at`, `updated_by`, `updated_at`, `description`) " +
	"VALUES " +
	"( 'admin', 'bkdata.superuser', 'global', 'active', DATE_ADD(NOW(), INTERVAL 30 DAY), 'system', NOW(), '', NOW(), '初始管理员超级权限' );"

type AuthUserRoleProviderTestSuite struct {
	suite.Suite
	mySqlContainer       *testhelper.MySQLContainerWrapper
	authUserRoleProvider provider.AuthUserRoleProvider
	ctx                  context.Context
}

func (suite *AuthUserRoleProviderTestSuite) SetupSuite() {
	suite.ctx = context.Background()
	mySqlContainer, err := testhelper.NewMySQLContainerWrapper(suite.ctx)
	if err != nil {
		log.Fatal(err)
	}
	suite.mySqlContainer = mySqlContainer
	db := testhelper.ExecSQL(mySqlContainer.ConnStr, "CREATE DATABASE IF NOT EXISTS bkdata_basic;")

	db, err = testhelper.InitDBConnection(mySqlContainer.ConnStr)
	if err != nil {
		log.Fatal(err)
	}
	dbAccess := dbaccess.NewAuthUserRoleDbAccess(db)
	authUserRoleProvider := provider.NewAuthUserRoleProvider(dbAccess)
	suite.authUserRoleProvider = authUserRoleProvider
}

func (suite *AuthUserRoleProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AuthUserRoleProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAuthUserRole, &model.AuthUserRoleModel{})
}

func TestAuthUserRoleProvider(t *testing.T) {
	suite.Run(t, new(AuthUserRoleProviderTestSuite))
}

func (suite *AuthUserRoleProviderTestSuite) TestFindAuthUserRolesByParams() {
	t := suite.T()

	testhelper.ExecSQL(suite.mySqlContainer.ConnStr, addSql)

	var params = &entitys.AuthUserRoleQueryParams{
		UserID: "admin",
		RoleID: commconst.AdminUserAuthRoleID,
	}

	foundAuthUserRoles := suite.authUserRoleProvider.CheckUserRole(*params)
	assert.NotNil(t, foundAuthUserRoles)
	assert.Equal(t, true, foundAuthUserRoles)
}
