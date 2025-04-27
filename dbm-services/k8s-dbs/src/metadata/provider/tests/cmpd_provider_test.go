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

func initCmpdTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_componentdefinition;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_componentdefinition table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentDefinitionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_componentdefinition table")
		return nil, err
	}
	return db, nil
}

func TestCreateComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentDefinitionDbAccess(db)

	cmpdProvider := provider.NewK8sCrdComponentDefinitionProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateComponentDefinition(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	var foundCmpd model.K8sCrdComponentDefinitionModel
	err = db.First(&foundCmpd, "componentdefinition_name=?", "mycmpd").Error
	assert.NoError(t, err, "Failed to query componentDefinition")
	assert.Equal(t, cmpd.ComponentDefinitionName, foundCmpd.ComponentDefinitionName)
	assert.Equal(t, cmpd.AddonID, foundCmpd.AddonID)
	assert.Equal(t, cmpd.DefaultVersion, foundCmpd.DefaultVersion)
	assert.Equal(t, cmpd.Metadata, foundCmpd.Metadata)
	assert.Equal(t, cmpd.Spec, foundCmpd.Spec)
	assert.Equal(t, cmpd.Active, foundCmpd.Active)
}

func TestDeletComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentDefinitionDbAccess(db)

	cmpdProvider := provider.NewK8sCrdComponentDefinitionProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateComponentDefinition(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	rows, err := cmpdProvider.DeleteComponentDefinitionById(1)
	assert.NoError(t, err, "Failed to delete componentDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentDefinitionDbAccess(db)

	cmpdProvider := provider.NewK8sCrdComponentDefinitionProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateComponentDefinition(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	updatedCmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ID:                      1,
		ComponentDefinitionName: "mycmpd2",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default2\"}",
		Spec:                    "{\"replicas\":2}",
		Active:                  false,
		Description:             "desc",
		UpdatedAt:               time.Now(),
	}
	rows, err := cmpdProvider.UpdateComponentDefinition(updatedCmpd)
	assert.NoError(t, err, "Failed to update componentDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentDefinitionDbAccess(db)

	cmpdProvider := provider.NewK8sCrdComponentDefinitionProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateComponentDefinition(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	foundCmpd, err := cmpdProvider.FindComponentDefinitionById(1)
	assert.NoError(t, err, "Failed to find componentDefinition")
	assert.Equal(t, cmpd.ComponentDefinitionName, foundCmpd.ComponentDefinitionName)
	assert.Equal(t, cmpd.AddonID, foundCmpd.AddonID)
	assert.Equal(t, cmpd.DefaultVersion, foundCmpd.DefaultVersion)
	assert.Equal(t, cmpd.Metadata, foundCmpd.Metadata)
	assert.Equal(t, cmpd.Spec, foundCmpd.Spec)
	assert.Equal(t, cmpd.Active, foundCmpd.Active)
}
