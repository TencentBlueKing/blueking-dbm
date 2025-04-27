package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sClusterServiceDbAccess interface {
	Create(model *models.K8sClusterServiceModel) (*models.K8sClusterServiceModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sClusterServiceModel, error)
	Update(model *models.K8sClusterServiceModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sClusterServiceModel, int64, error)
}

type K8sClusterServiceDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sClusterServiceDbAccessImpl) Create(model *models.K8sClusterServiceModel) (*models.K8sClusterServiceModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create service error", "error", err)
		return nil, err
	}
	var addedService models.K8sClusterServiceModel
	if err := k.db.First(&addedService, "id=?", model.ID).Error; err != nil {
		slog.Error("Find service error", "error", err)
		return nil, err
	} else {
		return &addedService, nil
	}
}

func (k *K8sClusterServiceDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sClusterServiceModel{}, id)
	if result.Error != nil {
		slog.Error("Delete service error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sClusterServiceDbAccessImpl) FindById(id uint64) (*models.K8sClusterServiceModel, error) {
	var request models.K8sClusterServiceModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		slog.Error("Find service error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &request, nil
	}
}

func (k *K8sClusterServiceDbAccessImpl) Update(model *models.K8sClusterServiceModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update service error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sClusterServiceDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sClusterServiceModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sClusterServiceDbAccess(db *gorm.DB) K8sClusterServiceDbAccess {
	return &K8sClusterServiceDbAccessImpl{db: db}
}
