package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sClusterConfigDbAccess interface {
	Create(model *models.K8sClusterConfigModel) (*models.K8sClusterConfigModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sClusterConfigModel, error)
	FindByClusterName(name string) (*models.K8sClusterConfigModel, error)
	Update(model *models.K8sClusterConfigModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sClusterConfigModel, int64, error)
}

type K8sClusterConfigDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sClusterConfigDbAccessImpl) FindByClusterName(name string) (*models.K8sClusterConfigModel, error) {
	var model models.K8sClusterConfigModel
	if err := k.db.First(&model, "cluster_name=?", name).Error; err != nil {
		slog.Error("Find model error", "error", err)
		return nil, err
	} else {
		return &model, nil
	}
}

func (k *K8sClusterConfigDbAccessImpl) Create(model *models.K8sClusterConfigModel) (*models.K8sClusterConfigModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	var addedModel models.K8sClusterConfigModel
	if err := k.db.First(&addedModel, "id=?", model.ID).Error; err != nil {
		slog.Error("Find model error", "error", err)
		return nil, err
	} else {
		return &addedModel, nil
	}
}

func (k *K8sClusterConfigDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sClusterConfigModel{}, id)
	if result.Error != nil {
		slog.Error("Delete model error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sClusterConfigDbAccessImpl) FindById(id uint64) (*models.K8sClusterConfigModel, error) {
	var model models.K8sClusterConfigModel
	result := k.db.First(&model, id)
	if result.Error != nil {
		slog.Error("Find model error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &model, nil
	}
}

func (k *K8sClusterConfigDbAccessImpl) Update(model *models.K8sClusterConfigModel) (uint64, error) {
	updatedModel := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if updatedModel.Error != nil {
		slog.Error("Update model error", "error", updatedModel.Error.Error())
		return 0, updatedModel.Error
	} else {
		return uint64(updatedModel.RowsAffected), nil
	}
}

func (k *K8sClusterConfigDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sClusterConfigModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sClusterConfigDbAccess(db *gorm.DB) K8sClusterConfigDbAccess {
	return &K8sClusterConfigDbAccessImpl{db: db}
}
