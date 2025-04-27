package dbaccess

import (
	"errors"
	"fmt"
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdClusterDbAccess interface {
	Create(model *models.K8sCrdClusterModel) (*models.K8sCrdClusterModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdClusterModel, error)
	FindByParams(params map[string]interface{}) (*models.K8sCrdClusterModel, error)
	Update(model *models.K8sCrdClusterModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdStorageAddonModel, int64, error)
}

type K8sCrdClusterDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sCrdClusterDbAccessImpl) Create(model *models.K8sCrdClusterModel) (*models.K8sCrdClusterModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create cluster error", "error", err)
		return nil, err
	}
	var addedCluster models.K8sCrdClusterModel
	if err := k.db.First(&addedCluster, "id=?", model.ID).Error; err != nil {
		slog.Error("Find cluster error", "error", err)
		return nil, err
	} else {
		return &addedCluster, nil
	}
}

func (k *K8sCrdClusterDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdClusterModel{}, id)
	if result.Error != nil {
		slog.Error("Delete cluster error:", "error", result.Error)
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdClusterDbAccessImpl) FindById(id uint64) (*models.K8sCrdClusterModel, error) {
	var cluster models.K8sCrdClusterModel
	result := k.db.First(&cluster, id)
	if result.Error != nil {
		slog.Error("Find cluster error", "error", result.Error)
		return nil, result.Error
	} else {
		return &cluster, nil
	}
}

func (k *K8sCrdClusterDbAccessImpl) FindByParams(params map[string]interface{}) (*models.K8sCrdClusterModel, error) {
	var cluster models.K8sCrdClusterModel

	// 动态条件查询
	result := k.db.Where(params).First(&cluster)

	if errors.Is(result.Error, gorm.ErrRecordNotFound) {
		return nil, fmt.Errorf("cluster not found")
	}
	if result.Error != nil {
		log.Printf("Query cluster error: %v", result.Error)
		return nil, result.Error
	}

	return &cluster, nil
}

func (k *K8sCrdClusterDbAccessImpl) Update(model *models.K8sCrdClusterModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update cluster error:", "error", result.Error)
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdClusterDbAccessImpl) ListByPage(_ utils.Pagination) ([]models.K8sCrdStorageAddonModel, int64, error) {
	panic("implement me")
}

func NewCrdClusterDbAccess(db *gorm.DB) K8sCrdClusterDbAccess {
	return &K8sCrdClusterDbAccessImpl{db: db}
}
