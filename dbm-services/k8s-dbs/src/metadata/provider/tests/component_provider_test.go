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

func initComponentTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_component;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_component table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_component table")
		return nil, err
	}
	return db, nil
}

func TestCreateComponent(t *testing.T) {
	db, err := initComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)

	componentProvider := provider.NewK8sCrdComponentProvider(dbAccess)

	component := &entitys.K8sCrdComponentEntity{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}

	addedComponent, err := componentProvider.CreateComponent(component)
	assert.NoError(t, err, "Failed to create component")
	fmt.Printf("Created component %+v\n", addedComponent)

	var foundComponent model.K8sCrdComponentModel
	err = db.First(&foundComponent, "component_name=?", "component-01").Error
	assert.NoError(t, err, "Failed to query component")
	assert.Equal(t, component.ComponentName, foundComponent.ComponentName)
	assert.Equal(t, component.CrdClusterID, foundComponent.CrdClusterID)
	assert.Equal(t, component.Status, foundComponent.Status)
}

func TestDeleteComponent(t *testing.T) {
	db, err := initComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)

	componentProvider := provider.NewK8sCrdComponentProvider(dbAccess)

	component := &entitys.K8sCrdComponentEntity{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}

	addedComponent, err := componentProvider.CreateComponent(component)
	assert.NoError(t, err, "Failed to create component")
	fmt.Printf("Created component %+v\n", addedComponent)

	rows, err := componentProvider.DeleteComponentById(1)
	assert.NoError(t, err, "Failed to delete component")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponent(t *testing.T) {
	db, err := initComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)

	componentProvider := provider.NewK8sCrdComponentProvider(dbAccess)

	component := &entitys.K8sCrdComponentEntity{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}

	addedComponent, err := componentProvider.CreateComponent(component)
	assert.NoError(t, err, "Failed to create component")
	fmt.Printf("Created cluster %+v\n", addedComponent)

	newComponent := &entitys.K8sCrdComponentEntity{
		ID:            1,
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Disable",
		Description:   "update component",
		UpdatedAt:     time.Now(),
	}
	rows, err := componentProvider.UpdateComponent(newComponent)
	assert.NoError(t, err, "Failed to update component")
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponent(t *testing.T) {
	db, err := initComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)

	componentProvider := provider.NewK8sCrdComponentProvider(dbAccess)

	component := &entitys.K8sCrdComponentEntity{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}

	addedComponent, err := componentProvider.CreateComponent(component)
	assert.NoError(t, err, "Failed to create component")
	fmt.Printf("Created component %+v\n", addedComponent)

	foundComponent, err := componentProvider.FindComponentById(1)
	assert.NoError(t, err, "Failed to find cluster")
	assert.Equal(t, component.ComponentName, foundComponent.ComponentName)
	assert.Equal(t, component.CrdClusterID, foundComponent.CrdClusterID)
	assert.Equal(t, component.Status, foundComponent.Status)
}
