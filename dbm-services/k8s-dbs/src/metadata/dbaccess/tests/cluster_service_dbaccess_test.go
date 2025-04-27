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

func InitK8sClusterServiceTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MYSQL_URL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_cluster_service;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_cluster_service table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sClusterServiceModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_cluster_service table")
		return nil, err
	}
	return db, nil
}

func TestCreateService(t *testing.T) {
	db, err := InitK8sClusterServiceTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterServiceDbAccess(db)

	service := &model.K8sClusterServiceModel{
		CrdClusterID:  1,
		ComponentName: "test-component",
		ServiceName:   "test-service",
		ServiceType:   "LoadBalancer",
		Annotations:   "{xxxxxx:xxxxxx}",
		InternalAddrs: "ip1:8080;ip2:8081",
		ExternalAddrs: "ip3:8080;ip3:8081",
		Domains:       "test-domain1;test-domain2",
		Description:   "desc",
	}

	added, err := dbAccess.Create(service)
	assert.NoError(t, err, "Failed to create service")
	fmt.Printf("Created config %+v\n", added)

	var founded model.K8sClusterServiceModel
	err = db.First(&founded, "service_name=?", service.ServiceName).Error
	assert.NoError(t, err, "Failed to query service")
	assert.Equal(t, service.CrdClusterID, founded.CrdClusterID)
	assert.Equal(t, service.ComponentName, founded.ComponentName)
	assert.Equal(t, service.ServiceName, founded.ServiceName)
	assert.Equal(t, service.ServiceType, founded.ServiceType)
	assert.Equal(t, service.Annotations, founded.Annotations)
	assert.Equal(t, service.InternalAddrs, founded.InternalAddrs)
	assert.Equal(t, service.ExternalAddrs, founded.ExternalAddrs)
	assert.Equal(t, service.Domains, founded.Domains)
}

func TestGetService(t *testing.T) {
	db, err := InitK8sClusterServiceTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterServiceDbAccess(db)

	service := &model.K8sClusterServiceModel{
		CrdClusterID:  1,
		ComponentName: "test-component",
		ServiceName:   "test-service",
		ServiceType:   "LoadBalancer",
		Annotations:   "{xxxxxx:xxxxxx}",
		InternalAddrs: "ip1:8080;ip2:8081",
		ExternalAddrs: "ip3:8080;ip3:8081",
		Domains:       "test-domain1;test-domain2",
		Description:   "desc",
	}

	added, err := dbAccess.Create(service)
	assert.NoError(t, err, "Failed to create service")
	fmt.Printf("Created config %+v\n", added)

	founded, err := dbAccess.FindById(1)
	assert.NoError(t, err, "Failed to query service")
	assert.Equal(t, service.CrdClusterID, founded.CrdClusterID)
	assert.Equal(t, service.ComponentName, founded.ComponentName)
	assert.Equal(t, service.ServiceName, founded.ServiceName)
	assert.Equal(t, service.ServiceType, founded.ServiceType)
	assert.Equal(t, service.Annotations, founded.Annotations)
	assert.Equal(t, service.InternalAddrs, founded.InternalAddrs)
	assert.Equal(t, service.ExternalAddrs, founded.ExternalAddrs)
	assert.Equal(t, service.Domains, founded.Domains)
}
