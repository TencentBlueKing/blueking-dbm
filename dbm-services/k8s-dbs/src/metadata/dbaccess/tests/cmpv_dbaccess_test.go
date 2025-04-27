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

func SetUpTestDBForCmpv() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_componentversion;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_componentversion table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentVersionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_componentversion table")
		return nil, err
	}
	return db, nil
}

func TestCreateComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := dbAccess.Create(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	var foundCmpv model.K8sCrdComponentVersionModel
	err = db.First(&foundCmpv, "componentversion_name=?", "mycmpv").Error
	assert.NoError(t, err, "Failed to query componentVersion")
	assert.Equal(t, cmpv.ComponentVersionName, foundCmpv.ComponentVersionName)
	assert.Equal(t, cmpv.AddonID, foundCmpv.AddonID)
	assert.Equal(t, cmpv.Metadata, foundCmpv.Metadata)
	assert.Equal(t, cmpv.Spec, foundCmpv.Spec)
	assert.Equal(t, cmpv.Active, foundCmpv.Active)
}

func TestDeletComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := dbAccess.Create(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	rows, err := dbAccess.DeleteById(1)
	assert.NoError(t, err, "Failed to delete componentVersion")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := dbAccess.Create(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	updatedCmpv := &model.K8sCrdComponentVersionModel{
		ID:                   1,
		ComponentVersionName: "mycmpv2",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default2\"}",
		Spec:                 "{\"replicas\":2}",
		Active:               false,
		Description:          "desc",
		UpdatedAt:            time.Now(),
	}
	rows, err := dbAccess.Update(updatedCmpv)
	assert.NoError(t, err, "Failed to update componentVersion")
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := dbAccess.Create(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	foundCmpv, err := dbAccess.FindById(1)
	assert.NoError(t, err, "Failed to find componentVersion")
	assert.Equal(t, cmpv.ComponentVersionName, foundCmpv.ComponentVersionName)
	assert.Equal(t, cmpv.AddonID, foundCmpv.AddonID)
	assert.Equal(t, cmpv.Metadata, foundCmpv.Metadata)
	assert.Equal(t, cmpv.Spec, foundCmpv.Spec)
	assert.Equal(t, cmpv.Active, foundCmpv.Active)
}
