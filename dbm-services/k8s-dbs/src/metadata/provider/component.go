package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdComponentProvider interface {
	CreateComponent(entity *entitys.K8sCrdComponentEntity) (*entitys.K8sCrdComponentEntity, error)
	DeleteComponentById(id uint64) (uint64, error)
	FindComponentById(id uint64) (*entitys.K8sCrdComponentEntity, error)
	UpdateComponent(entity *entitys.K8sCrdComponentEntity) (uint64, error)
}

type K8sCrdComponentProviderImpl struct {
	dbAccess dbaccess.K8sCrdComponentDbAccess
}

func (k K8sCrdComponentProviderImpl) CreateComponent(entity *entitys.K8sCrdComponentEntity) (*entitys.K8sCrdComponentEntity, error) {
	k8sCrdComponentModel := models.K8sCrdComponentModel{}
	err := copier.Copy(&k8sCrdComponentModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	componentModel, err := k.dbAccess.Create(&k8sCrdComponentModel)
	if err != nil {
		slog.Error("Failed to create entity", "error", err)
		return nil, err
	} else {
		componentEntity := entitys.K8sCrdComponentEntity{}
		err := copier.Copy(&componentEntity, componentModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &componentEntity, nil
		}
	}
}

func (k K8sCrdComponentProviderImpl) DeleteComponentById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k K8sCrdComponentProviderImpl) FindComponentById(id uint64) (*entitys.K8sCrdComponentEntity, error) {
	componentModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		componentEntity := entitys.K8sCrdComponentEntity{}
		err := copier.Copy(&componentEntity, componentModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &componentEntity, nil
		}
	}
}

func (k K8sCrdComponentProviderImpl) UpdateComponent(entity *entitys.K8sCrdComponentEntity) (uint64, error) {
	componentModel := models.K8sCrdComponentModel{}
	err := copier.Copy(&componentModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&componentModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdComponentProvider(dbAccess dbaccess.K8sCrdComponentDbAccess) K8sCrdComponentProvider {
	return &K8sCrdComponentProviderImpl{dbAccess}
}
