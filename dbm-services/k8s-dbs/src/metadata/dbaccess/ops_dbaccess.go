package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdOpsRequestDbAccess interface {
	Create(model *models.K8sCrdOpsRequestModel) (*models.K8sCrdOpsRequestModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdOpsRequestModel, error)
	Update(model *models.K8sCrdOpsRequestModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdOpsRequestModel, int64, error)
}

type K8sCrdOpsRequestDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sCrdOpsRequestDbAccessImpl) Create(model *models.K8sCrdOpsRequestModel) (*models.K8sCrdOpsRequestModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create ops error", "error", err)
		return nil, err
	}
	var addedOps models.K8sCrdOpsRequestModel
	if err := k.db.First(&addedOps, "id=?", model.ID).Error; err != nil {
		slog.Error("Find ops error", "error", err)
		return nil, err
	} else {
		return &addedOps, nil
	}
}

func (k *K8sCrdOpsRequestDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdOpsRequestModel{}, id)
	if result.Error != nil {
		slog.Error("Delete ops error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdOpsRequestDbAccessImpl) FindById(id uint64) (*models.K8sCrdOpsRequestModel, error) {
	var ops models.K8sCrdOpsRequestModel
	result := k.db.First(&ops, id)
	if result.Error != nil {
		slog.Error("Find ops error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &ops, nil
	}
}

func (k *K8sCrdOpsRequestDbAccessImpl) Update(model *models.K8sCrdOpsRequestModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update ops error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdOpsRequestDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sCrdOpsRequestModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sCrdOpsRequestDbAccess(db *gorm.DB) K8sCrdOpsRequestDbAccess {
	return &K8sCrdOpsRequestDbAccessImpl{db: db}
}
