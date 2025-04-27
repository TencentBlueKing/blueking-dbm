package tests

import (
	"fmt"
	"k8s-dbs/src/metadata/constant"
	"k8s-dbs/src/metadata/dbaccess"
	"k8s-dbs/src/metadata/dbaccess/model"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initClusterTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_cluster;").Error; err != nil {
		fmt.Println("Failed to drop k8s_crd_clusters table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdClusterModel{}); err != nil {
		fmt.Println("Failed to migrate k8s_crd_clusters table")
		return nil, err
	}
	return db, nil
}

func TestCreateCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)

	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		K8sClusterConfigId: 1,
		RequestId:          1,
		Namespace:          "default",
		Status:             "Enable",
		Description:        "desc",
	}

	addedCluster, err := dbAccess.Create(cluster)
	assert.NoError(t, err, "Failed to create cluster")
	fmt.Printf("Created cluster %+v\n", addedCluster)

	var foundCluster model.K8sCrdClusterModel
	err = db.First(&foundCluster, "cluster_name=?", "mycluster").Error
	assert.NoError(t, err, "Failed to query cluster")
	assert.Equal(t, cluster.ClusterName, foundCluster.ClusterName)
	assert.Equal(t, cluster.Namespace, foundCluster.Namespace)
	assert.Equal(t, cluster.Status, foundCluster.Status)
	assert.Equal(t, cluster.AddonID, foundCluster.AddonID)
}

func TestDeleteCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigId: 1,
		RequestId:          1,
		Status:             "Enable",
		Description:        "desc",
	}
	addedCluster, err := dbAccess.Create(cluster)
	assert.NoError(t, err, "Failed to create cluster")
	fmt.Printf("Created cluster %+v\n", addedCluster)

	rows, err := dbAccess.DeleteById(1)
	assert.NoError(t, err, "Failed to delete cluster")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigId: 1,
		RequestId:          1,
		Status:             "Enable",
		Description:        "desc",
	}
	addedCluster, err := dbAccess.Create(cluster)
	assert.NoError(t, err, "Failed to create cluster")
	fmt.Printf("Created cluster %+v\n", addedCluster)

	newCluster := &model.K8sCrdClusterModel{
		ID:          1,
		ClusterName: "mycluster2",
		Namespace:   "default2",
		Status:      "Disable",
		Description: "desc desc",
		UpdatedAt:   time.Now(),
	}
	rows, err := dbAccess.Update(newCluster)
	assert.NoError(t, err, "Failed to update cluster")
	assert.Equal(t, uint64(1), rows)
}

func TestGetCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigId: 1,
		RequestId:          1,
		Status:             "Enable",
		Description:        "desc",
	}
	addedCluster, err := dbAccess.Create(cluster)
	assert.NoError(t, err, "Failed to create cluster")
	fmt.Printf("Created cluster %+v\n", addedCluster)

	findCluster, err := dbAccess.FindById(1)
	assert.NoError(t, err, "Failed to find cluster")
	assert.Equal(t, cluster.ClusterName, findCluster.ClusterName)
	assert.Equal(t, cluster.Namespace, findCluster.Namespace)
	assert.Equal(t, cluster.Status, findCluster.Status)
	assert.Equal(t, cluster.AddonID, findCluster.AddonID)
}

func TestGetClusterByParams(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigId: 1,
		RequestId:          1,
		Status:             "Enable",
		Description:        "desc",
	}
	addedCluster, err := dbAccess.Create(cluster)
	assert.NoError(t, err, "Failed to create cluster")
	fmt.Printf("Created cluster %+v\n", addedCluster)

	params := map[string]interface{}{
		"cluster_name": "mycluster",
		"namespace":    "default",
	}
	findCluster, err := dbAccess.FindByParams(params)
	assert.NoError(t, err, "Failed to find cluster")
	assert.Equal(t, cluster.ClusterName, findCluster.ClusterName)
	assert.Equal(t, cluster.Namespace, findCluster.Namespace)
	assert.Equal(t, cluster.Status, findCluster.Status)
	assert.Equal(t, cluster.AddonID, findCluster.AddonID)
}
