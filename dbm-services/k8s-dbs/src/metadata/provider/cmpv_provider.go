package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdComponentVersionProvider interface {
	CreateComponentVersion(entity *entitys.K8sCrdComponentVersionEntity) (*entitys.K8sCrdComponentVersionEntity, error)
	DeleteComponentVersionById(id uint64) (uint64, error)
	FindComponentVersionById(id uint64) (*entitys.K8sCrdComponentVersionEntity, error)
	UpdateComponentVersion(entity *entitys.K8sCrdComponentVersionEntity) (uint64, error)
}

type K8sCrdComponentVersionProviderImpl struct {
	dbAccess dbaccess.K8sCrdComponentVersionDbAccess
}

func (k *K8sCrdComponentVersionProviderImpl) CreateComponentVersion(entity *entitys.K8sCrdComponentVersionEntity) (*entitys.K8sCrdComponentVersionEntity, error) {
	cmpvModel := models.K8sCrdComponentVersionModel{}
	err := copier.Copy(&cmpvModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedCmpvModel, err := k.dbAccess.Create(&cmpvModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	} else {
		cmpvEntity := entitys.K8sCrdComponentVersionEntity{}
		err := copier.Copy(&cmpvEntity, addedCmpvModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &cmpvEntity, nil
		}
	}
}

func (k *K8sCrdComponentVersionProviderImpl) DeleteComponentVersionById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sCrdComponentVersionProviderImpl) FindComponentVersionById(id uint64) (*entitys.K8sCrdComponentVersionEntity, error) {
	cmpvModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		cmpvEntity := entitys.K8sCrdComponentVersionEntity{}
		err := copier.Copy(&cmpvEntity, cmpvModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &cmpvEntity, nil
		}
	}
}

func (k *K8sCrdComponentVersionProviderImpl) UpdateComponentVersion(entity *entitys.K8sCrdComponentVersionEntity) (uint64, error) {
	cmpvModel := models.K8sCrdComponentVersionModel{}
	err := copier.Copy(&cmpvModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&cmpvModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdComponentVersionProvider(dbAccess dbaccess.K8sCrdComponentVersionDbAccess) K8sCrdComponentVersionProvider {
	return &K8sCrdComponentVersionProviderImpl{dbAccess}
}
