package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdClusterDefinitionDbAccess interface {
	Create(model *models.K8sCrdClusterDefinitionModel) (*models.K8sCrdClusterDefinitionModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdClusterDefinitionModel, error)
	Update(model *models.K8sCrdClusterDefinitionModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdClusterDefinitionModel, int64, error)
}

type K8sCrdClusterDefinitionDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sCrdClusterDefinitionDbAccessImpl) Create(clusterDefModel *models.K8sCrdClusterDefinitionModel) (*models.K8sCrdClusterDefinitionModel, error) {
	if err := k.db.Create(clusterDefModel).Error; err != nil {
		slog.Error("Create clusterdefinition error", "error", err)
		return nil, err
	}
	var addedClusterDefModel models.K8sCrdClusterDefinitionModel
	if err := k.db.First(&addedClusterDefModel, "clusterdefinition_name = ?", clusterDefModel.ClusterDefinitionName).Error; err != nil {
		slog.Error("Find clusterdefinition error", "error", err)
		return nil, err
	} else {
		return &addedClusterDefModel, nil
	}
}

func (k *K8sCrdClusterDefinitionDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdClusterDefinitionModel{}, id)
	if result.Error != nil {
		slog.Error("Delete clusterdefinition error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdClusterDefinitionDbAccessImpl) FindById(id uint64) (*models.K8sCrdClusterDefinitionModel, error) {
	var clusterDefModel models.K8sCrdClusterDefinitionModel
	result := k.db.First(&clusterDefModel, id)
	if result.Error != nil {
		slog.Error("Find clusterdefinition error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &clusterDefModel, nil
	}
}

func (k *K8sCrdClusterDefinitionDbAccessImpl) Update(clusterDefModel *models.K8sCrdClusterDefinitionModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(clusterDefModel)
	if result.Error != nil {
		slog.Error("Update clusterdefinition error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdClusterDefinitionDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sCrdClusterDefinitionModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sCrdClusterDefinitionDbAccess(db *gorm.DB) K8sCrdClusterDefinitionDbAccess {
	return &K8sCrdClusterDefinitionDbAccessImpl{db: db}
}
