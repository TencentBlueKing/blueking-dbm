package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdComponentVersionDbAccess interface {
	Create(model *models.K8sCrdComponentVersionModel) (*models.K8sCrdComponentVersionModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdComponentVersionModel, error)
	Update(model *models.K8sCrdComponentVersionModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentVersionModel, int64, error)
}

type K8sCrdComponentVersionDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sCrdComponentVersionDbAccessImpl) Create(cmpvModel *models.K8sCrdComponentVersionModel) (*models.K8sCrdComponentVersionModel, error) {
	if err := k.db.Create(cmpvModel).Error; err != nil {
		slog.Error("Create componentversion error", "error", err)
		return nil, err
	}
	var addedCmpvModel models.K8sCrdComponentVersionModel
	if err := k.db.First(&addedCmpvModel, "componentversion_name = ?", cmpvModel.ComponentVersionName).Error; err != nil {
		slog.Error("Find componentversion error", "error", err)
		return nil, err
	} else {
		return &addedCmpvModel, nil
	}
}

func (k *K8sCrdComponentVersionDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdComponentVersionModel{}, id)
	if result.Error != nil {
		slog.Error("Delete componentversion error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdComponentVersionDbAccessImpl) FindById(id uint64) (*models.K8sCrdComponentVersionModel, error) {
	var cmpvModel models.K8sCrdComponentVersionModel
	result := k.db.First(&cmpvModel, id)
	if result.Error != nil {
		slog.Error("Find componentversion error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &cmpvModel, nil
	}
}

func (k *K8sCrdComponentVersionDbAccessImpl) Update(cmpvModel *models.K8sCrdComponentVersionModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(cmpvModel)
	if result.Error != nil {
		slog.Error("Update componentversion error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdComponentVersionDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentVersionModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sCrdComponentVersionDbAccess(db *gorm.DB) K8sCrdComponentVersionDbAccess {
	return &K8sCrdComponentVersionDbAccessImpl{db: db}
}
