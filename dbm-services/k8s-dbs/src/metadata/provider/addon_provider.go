package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdStorageAddonProvider interface {
	CreateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (*entitys.K8sCrdStorageAddonEntity, error)
	DeleteStorageAddonById(id uint64) (uint64, error)
	FindStorageAddonById(id uint64) (*entitys.K8sCrdStorageAddonEntity, error)
	UpdateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (uint64, error)
}

type K8sCrdStorageAddonProviderImpl struct {
	dbAccess dbaccess.K8sCrdStorageAddonDbAccess
}

func (k *K8sCrdStorageAddonProviderImpl) CreateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (*entitys.K8sCrdStorageAddonEntity, error) {
	storageAddonModel := models.K8sCrdStorageAddonModel{}
	err := copier.Copy(&storageAddonModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedStorageAddonModel, err := k.dbAccess.Create(&storageAddonModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	} else {
		storageAddonEntity := entitys.K8sCrdStorageAddonEntity{}
		err := copier.Copy(&storageAddonEntity, addedStorageAddonModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &storageAddonEntity, nil
		}
	}
}

func (k *K8sCrdStorageAddonProviderImpl) DeleteStorageAddonById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sCrdStorageAddonProviderImpl) FindStorageAddonById(id uint64) (*entitys.K8sCrdStorageAddonEntity, error) {
	storageAddonModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	} else {
		storageAddonEntity := entitys.K8sCrdStorageAddonEntity{}
		err := copier.Copy(&storageAddonEntity, storageAddonModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &storageAddonEntity, nil
		}
	}
}

func (k *K8sCrdStorageAddonProviderImpl) UpdateStorageAddon(entity *entitys.K8sCrdStorageAddonEntity) (uint64, error) {
	storageAddonModel := models.K8sCrdStorageAddonModel{}
	err := copier.Copy(&storageAddonModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&storageAddonModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdStorageAddonProvider(dbAccess dbaccess.K8sCrdStorageAddonDbAccess) K8sCrdStorageAddonProvider {
	return &K8sCrdStorageAddonProviderImpl{dbAccess: dbAccess}
}
