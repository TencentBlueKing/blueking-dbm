package tests

import (
	"fmt"
	"k8s-dbs/src/metadata/constant"
	"k8s-dbs/src/metadata/dbaccess"
	"k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/provider"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initCmpvTable() (*gorm.DB, error) {
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
	db, err := initCmpvTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpvProvider := provider.NewK8sCrdComponentVersionProvider(dbAccess)

	cmpv := &entitys.K8sCrdComponentVersionEntity{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := cmpvProvider.CreateComponentVersion(cmpv)
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
	db, err := initCmpvTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpvProvider := provider.NewK8sCrdComponentVersionProvider(dbAccess)

	cmpv := &entitys.K8sCrdComponentVersionEntity{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := cmpvProvider.CreateComponentVersion(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	rows, err := cmpvProvider.DeleteComponentVersionById(1)
	assert.NoError(t, err, "Failed to delete componentVersion")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponentVersion(t *testing.T) {
	db, err := initCmpvTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpvProvider := provider.NewK8sCrdComponentVersionProvider(dbAccess)

	cmpv := &entitys.K8sCrdComponentVersionEntity{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := cmpvProvider.CreateComponentVersion(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	updatedCmpv := &entitys.K8sCrdComponentVersionEntity{
		ID:                   1,
		ComponentVersionName: "mycmpv2",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default2\"}",
		Spec:                 "{\"replicas\":2}",
		Active:               false,
		Description:          "desc",
		UpdatedAt:            time.Now(),
	}
	rows, err := cmpvProvider.UpdateComponentVersion(updatedCmpv)
	assert.NoError(t, err, "Failed to update componentVersion")
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponentVersion(t *testing.T) {
	db, err := initCmpvTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)

	cmpvProvider := provider.NewK8sCrdComponentVersionProvider(dbAccess)

	cmpv := &entitys.K8sCrdComponentVersionEntity{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := cmpvProvider.CreateComponentVersion(cmpv)
	assert.NoError(t, err, "Failed to create componentVersion")
	fmt.Printf("Created componentVersion %+v\n", addedCmpv)

	foundCmpv, err := cmpvProvider.FindComponentVersionById(1)
	assert.NoError(t, err, "Failed to find componentVersion")
	assert.Equal(t, cmpv.ComponentVersionName, foundCmpv.ComponentVersionName)
	assert.Equal(t, cmpv.AddonID, foundCmpv.AddonID)
	assert.Equal(t, cmpv.Metadata, foundCmpv.Metadata)
	assert.Equal(t, cmpv.Spec, foundCmpv.Spec)
	assert.Equal(t, cmpv.Active, foundCmpv.Active)
}
