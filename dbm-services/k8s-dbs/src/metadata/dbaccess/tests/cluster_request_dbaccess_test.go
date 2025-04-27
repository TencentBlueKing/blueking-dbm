package tests

import (
	"fmt"
	"k8s-dbs/src/metadata/constant"
	"k8s-dbs/src/metadata/dbaccess"
	"k8s-dbs/src/metadata/dbaccess/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitRequestRecordTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_cluster_request_record;").Error; err != nil {
		fmt.Println("Failed to drop tb_cluster_request_record table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.ClusterRequestRecordModel{}); err != nil {
		fmt.Println("Failed to migrate tb_cluster_request_record table")
		return nil, err
	}
	return db, nil
}

func TestCreateRequest(t *testing.T) {
	db, err := InitRequestRecordTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)

	request := &model.ClusterRequestRecordModel{
		RequestId:     "test-request-id",
		RequestParams: "test params",
		RequestType:   "Create",
		Description:   "desc",
		CreatedBy:     "Admin",
	}

	added, err := dbAccess.Create(request)
	assert.NoError(t, err, "Failed to create request")
	fmt.Printf("Created request %+v\n", added)

	var founded model.ClusterRequestRecordModel
	err = db.First(&founded, "request_id=?", request.RequestId).Error
	assert.NoError(t, err, "Failed to query request")
	assert.Equal(t, request.RequestId, founded.RequestId)
	assert.Equal(t, request.RequestParams, founded.RequestParams)
	assert.Equal(t, request.RequestType, founded.RequestType)
	assert.Equal(t, request.Description, founded.Description)
	assert.Equal(t, request.CreatedBy, founded.CreatedBy)
}

func TestGetRequest(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)

	request := &model.ClusterRequestRecordModel{
		RequestId:     "test-request-id",
		RequestParams: "test params",
		RequestType:   "Create",
		Description:   "desc",
		CreatedBy:     "Admin",
	}

	added, err := dbAccess.Create(request)
	assert.NoError(t, err, "Failed to create request")
	fmt.Printf("Created request %+v\n", added)

	founded, err := dbAccess.FindById(1)
	assert.NoError(t, err, "Failed to query request")
	assert.Equal(t, request.RequestId, founded.RequestId)
	assert.Equal(t, request.RequestParams, founded.RequestParams)
	assert.Equal(t, request.RequestType, founded.RequestType)
	assert.Equal(t, request.Description, founded.Description)
	assert.Equal(t, request.CreatedBy, founded.CreatedBy)
}
