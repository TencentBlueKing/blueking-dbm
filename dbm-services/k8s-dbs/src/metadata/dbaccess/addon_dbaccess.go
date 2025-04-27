package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdStorageAddonDbAccess interface {
	Create(model *models.K8sCrdStorageAddonModel) (*models.K8sCrdStorageAddonModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdStorageAddonModel, error)
	Update(model *models.K8sCrdStorageAddonModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdStorageAddonModel, int64, error)
}

type K8sCrdStorageAddonDbAccessImpl struct {
	db *gorm.DB
}

func (k *K8sCrdStorageAddonDbAccessImpl) Create(storageAddonModel *models.K8sCrdStorageAddonModel) (*models.K8sCrdStorageAddonModel, error) {
	if err := k.db.Create(storageAddonModel).Error; err != nil {
		slog.Error("Create storageAddon error", "error", err)
		return nil, err
	}
	var addedStorageAddonModel models.K8sCrdStorageAddonModel
	if err := k.db.First(&addedStorageAddonModel, "addon_name = ?", storageAddonModel.AddonName).Error; err != nil {
		slog.Error("Find storageAddon error", "error", err)
		return nil, err
	} else {
		return &addedStorageAddonModel, nil
	}
}

func (k *K8sCrdStorageAddonDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.K8sCrdStorageAddonModel{}, id)
	if result.Error != nil {
		slog.Error("Delete storageAddon error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdStorageAddonDbAccessImpl) FindById(id uint64) (*models.K8sCrdStorageAddonModel, error) {
	var storageAddonModel models.K8sCrdStorageAddonModel
	result := k.db.First(&storageAddonModel, id)
	if result.Error != nil {
		slog.Error("Find storageAddon error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &storageAddonModel, nil
	}
}

func (k *K8sCrdStorageAddonDbAccessImpl) Update(storageAddonModel *models.K8sCrdStorageAddonModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(storageAddonModel)
	if result.Error != nil {
		slog.Error("Update storageAddon error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *K8sCrdStorageAddonDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sCrdStorageAddonModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sCrdStorageAddonDbAccess(db *gorm.DB) K8sCrdStorageAddonDbAccess {
	return &K8sCrdStorageAddonDbAccessImpl{db: db}
}
