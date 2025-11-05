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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addSql = "INSERT INTO `bkdata_basic`.`auth_user_role`" +
	"( `user_id`, `role_id`, `scope_id`, `auth_status`, `expired_date`, `created_by`, `created_at`, `updated_by`, `updated_at`, `description`) " +
	"VALUES " +
	"( 'admin', 'bkdata.superuser', 'global', 'active', DATE_ADD(NOW(), INTERVAL 30 DAY), 'system', NOW(), '', NOW(), '初始管理员超级权限' );"

type AuthUserRoleDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AuthUserRoleDbAccess
	ctx            context.Context
}

func (suite *AuthUserRoleDbAccessTestSuite) SetupSuite() {
	suite.ctx = context.Background()
	mySqlContainer, err := testhelper.NewMySQLContainerWrapper(suite.ctx)
	if err != nil {
		log.Fatal(err)
	}
	suite.mySqlContainer = mySqlContainer

	// 先创建bkdata_basic数据库
	db := testhelper.ExecSQL(suite.mySqlContainer.ConnStr, "CREATE DATABASE IF NOT EXISTS bkdata_basic;")

	// 连接到创建好的数据库
	dsn := strings.Replace(suite.mySqlContainer.ConnStr, "dbname=", "dbname=bkdata_basic", 1)
	db, err = testhelper.InitDBConnection(dsn)
	if err != nil {
		log.Fatal(err)
	}

	// 初始化dbAccess
	suite.dbAccess = dbaccess.NewAuthUserRoleDbAccess(db)
}

func (suite *AuthUserRoleDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AuthUserRoleDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAuthUserRole, &model.AuthUserRoleModel{})
}

func (suite *AuthUserRoleDbAccessTestSuite) TestFindByParams() {
	t := suite.T()

	testhelper.ExecSQL(suite.mySqlContainer.ConnStr, addSql)

	params := metaentity.AuthUserRoleQueryParams{
		UserID: "admin",
		RoleID: commconst.AdminUserAuthRoleID,
	}

	authUserRoleEntitys, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)

	assert.Equal(t, 1, len(authUserRoleEntitys))
	assert.Equal(t, params.UserID, authUserRoleEntitys[0].UserID)
	assert.Equal(t, params.RoleID, authUserRoleEntitys[0].RoleID)
}

func TestAuthUserRoleDbAccess(t *testing.T) {
	suite.Run(t, new(AuthUserRoleDbAccessTestSuite))
}
