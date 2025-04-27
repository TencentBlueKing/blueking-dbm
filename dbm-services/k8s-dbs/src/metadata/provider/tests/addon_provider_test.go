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

func initAddonTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_storageaddon;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_storageaddon table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdStorageAddonModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_storageaddon table")
		return nil, err
	}
	return db, nil
}

func TestCreateStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	var foundStorageAddon model.K8sCrdStorageAddonModel
	err = db.First(&foundStorageAddon, "addon_name=?", "myaddon").Error
	assert.NoError(t, err, "Failed to query storageAddon")
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.Metadata, foundStorageAddon.Metadata)
	assert.Equal(t, storageAddon.Spec, foundStorageAddon.Spec)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}

func TestDeleteStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	rows, err := addonProvider.DeleteStorageAddonById(1)
	assert.NoError(t, err, "Failed to delete storageAddon")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	updateStorageAddon := &entitys.K8sCrdStorageAddonEntity{
		ID:            1,
		AddonName:     "myaddon2",
		AddonCategory: "Graph",
		AddonType:     "surrealdb2",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":1}",
		Active:        false,
		Description:   "desc",
		UpdatedAt:     time.Now(),
	}
	rows, err := addonProvider.UpdateStorageAddon(updateStorageAddon)
	assert.NoError(t, err, "Failed to update storageAddon")
	assert.Equal(t, uint64(1), rows)
}

func TestGetStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	foundStorageAddon, err := addonProvider.FindStorageAddonById(1)
	assert.NoError(t, err, "Failed to find storageAddon")
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.Metadata, foundStorageAddon.Metadata)
	assert.Equal(t, storageAddon.Spec, foundStorageAddon.Spec)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}
