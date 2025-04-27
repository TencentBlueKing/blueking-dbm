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

func SetUpTestDBForCd() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_clusterdefinition;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_clusterdefinition table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdClusterDefinitionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_clusterdefinition table")
		return nil, err
	}
	return db, nil
}

func TestCreateClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		ClusterDefinitionName: "cd1",
		AddonID:               uint64(1),
		Metadata:              "{\"namespace\":\"default\"}",
		Spec:                  "{\"replicas\":3}",
		Active:                true,
		Description:           "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created componentVersion %+v\n", addedCd)

	var foundCd model.K8sCrdClusterDefinitionModel
	err = db.First(&foundCd, "clusterdefinition_name=?", "cd1").Error
	assert.NoError(t, err, "Failed to query clusterDefinition")
	assert.Equal(t, cd.ClusterDefinitionName, foundCd.ClusterDefinitionName)
	assert.Equal(t, cd.AddonID, foundCd.AddonID)
	assert.Equal(t, cd.Metadata, foundCd.Metadata)
	assert.Equal(t, cd.Spec, foundCd.Spec)
	assert.Equal(t, cd.Active, foundCd.Active)
}

func TestDeletClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		ClusterDefinitionName: "cd1",
		AddonID:               uint64(1),
		Metadata:              "{\"namespace\":\"default\"}",
		Spec:                  "{\"replicas\":3}",
		Active:                true,
		Description:           "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created componentVersion %+v\n", addedCd)

	rows, err := dbAccess.DeleteById(1)
	assert.NoError(t, err, "Failed to delete clusterDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		ClusterDefinitionName: "cd1",
		AddonID:               uint64(1),
		Metadata:              "{\"namespace\":\"default\"}",
		Spec:                  "{\"replicas\":3}",
		Active:                true,
		Description:           "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created componentVersion %+v\n", addedCd)

	updatedCd := &model.K8sCrdClusterDefinitionModel{
		ID:                    1,
		ClusterDefinitionName: "cd2",
		AddonID:               uint64(1),
		Metadata:              "{\"namespace\":\"default2\"}",
		Spec:                  "{\"replicas\":2}",
		Active:                false,
		Description:           "desc",
		UpdatedAt:             time.Now(),
	}
	rows, err := dbAccess.Update(updatedCd)
	assert.NoError(t, err, "Failed to update clusterDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestGetClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		ClusterDefinitionName: "cd1",
		AddonID:               uint64(1),
		Metadata:              "{\"namespace\":\"default\"}",
		Spec:                  "{\"replicas\":3}",
		Active:                true,
		Description:           "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created clusterDefinition %+v\n", addedCd)

	foundCd, err := dbAccess.FindById(1)
	assert.NoError(t, err, "Failed to find clusterDefinition")
	assert.Equal(t, cd.ClusterDefinitionName, foundCd.ClusterDefinitionName)
	assert.Equal(t, cd.AddonID, foundCd.AddonID)
	assert.Equal(t, cd.Metadata, foundCd.Metadata)
	assert.Equal(t, cd.Spec, foundCd.Spec)
	assert.Equal(t, cd.Active, foundCd.Active)
}
