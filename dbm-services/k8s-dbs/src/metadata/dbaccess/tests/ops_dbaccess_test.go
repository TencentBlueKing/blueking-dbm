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

func InitOpsTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_opsrequest;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_opsrequest table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdOpsRequestModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_opsrequest table")
		return nil, err
	}
	return db, nil
}

func TestCreateOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigId: 1,
		RequestId:          1,
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	var foundOps model.K8sCrdOpsRequestModel
	err = db.First(&foundOps, "opsrequest_name=?", "greptimedb-restart").Error
	assert.NoError(t, err, "Failed to query ops")
	assert.Equal(t, ops.OpsRequestName, foundOps.OpsRequestName)
	assert.Equal(t, ops.OpsRequestType, foundOps.OpsRequestType)
	assert.Equal(t, ops.K8sClusterConfigId, foundOps.K8sClusterConfigId)
	assert.Equal(t, ops.RequestId, foundOps.RequestId)
	assert.Equal(t, ops.CrdClusterID, foundOps.CrdClusterID)
	assert.Equal(t, ops.Metadata, foundOps.Metadata)
	assert.Equal(t, ops.Status, foundOps.Status)
	assert.Equal(t, ops.Spec, foundOps.Spec)
}

func TestDeleteOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigId: 1,
		RequestId:          1,
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	rows, err := dbAccess.DeleteById(1)
	assert.NoError(t, err, "Failed to delete ops")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigId: 1,
		RequestId:          1,
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	newOps := &model.K8sCrdOpsRequestModel{
		ID:             1,
		OpsRequestName: "greptimedb-restart",
		OpsRequestType: "Start",
		CrdClusterID:   1,
		Metadata:       "{\"namespace\":\"default\"}",
		Spec:           "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:         "Finished",
		Description:    "desc",
	}
	rows, err := dbAccess.Update(newOps)
	assert.NoError(t, err, "Failed to update ops")
	assert.Equal(t, uint64(1), rows)
}

func TestGetOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigId: 1,
		RequestId:          1,
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	foundOps, err := dbAccess.FindById(1)
	assert.NoError(t, err, "Failed to find ops")
	assert.NoError(t, err, "Failed to query ops")
	assert.Equal(t, ops.OpsRequestName, foundOps.OpsRequestName)
	assert.Equal(t, ops.OpsRequestType, foundOps.OpsRequestType)
	assert.Equal(t, ops.CrdClusterID, foundOps.CrdClusterID)
	assert.Equal(t, ops.K8sClusterConfigId, foundOps.K8sClusterConfigId)
	assert.Equal(t, ops.RequestId, foundOps.RequestId)
	assert.Equal(t, ops.Metadata, foundOps.Metadata)
	assert.Equal(t, ops.Status, foundOps.Status)
	assert.Equal(t, ops.Spec, foundOps.Spec)
}
